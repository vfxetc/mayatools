from __future__ import print_function

import os
import re
import sys
import re
import xml.etree.ElementTree as etree
from collections import OrderedDict as odict

from metatools.imports.entry_points import load_entry_point, EntryPointMalformed


try:
    from maya import mel, cmds
except ImportError:
    pass


def find_descriptor(name):
    '''

    Defaults are found at:
        macOS: /Applications/Autodesk/maya2018/Maya.app/Contents/bin/rendererDesc
                                             ./Maya.app/Contents/bin/rendererDesc
                                             ./Maya.app/Contents/MacOS/rendererDesc
                                             ./Maya.app/Contents/Resources/rendererDesc
        Linux: /usr/autodesk/maya2018/bin/rendererDesc
    
    Can find these beside the executable.
        >>> sys.executable
        '/usr/autodesk/maya2016/bin/python-bin' # Linux.
        '/Applications/Autodesk/maya2018/Maya.app/Contents/MacOS/Maya' # macOS.
    
    # They say to use this.
    # RenderMan wasn't on the list until it was loaded.
    # But that is okay because the real Render loads the scene and then
    # goes looking for renderers.
    MAYA_RENDER_DESC_PATH
        /Applications/solidangle/mtoa/2018
        /Applications/Pixar/RenderManForMaya-22.1/etc

    '''

    if name.endswith('Renderer.xml'):
        filename = name
    else:
        filename = name + 'Renderer.xml'

    roots = ['.']
    
    # Beside the binaries.
    try:
        roots.append(os.path.abspath(os.path.join(os.environ['MAYA_LOCATION'], 'bin', 'rendererDesc')))
    except KeyError:
        roots.append(os.path.abspath(os.path.join(sys.executable, '..', 'rendererDesc')))

    # Where plugins have indicated they are.
    try:
        roots.extend(os.environ['MAYA_RENDER_DESC_PATH'].split(':'))
    except KeyError:
        pass

    for dir_ in roots:
        path = os.path.join(dir_, filename)
        if os.path.exists(path):
            return path

    raise ValueError("Could not find {}".format(filename))


class Action(object):

    @classmethod
    def from_node(cls, node):
        self = cls(**node.attrib)
        if node.tag == 'melheader':
            self.name = '__init__'
        if node.tag == 'meltrailer':
            self.name = '__main__'
        return self

    def __init__(self, n=None, s=None, t=None, h=None, p=None, desc=None):
        self.name = n
        self.source = s
        self.type = t
        self.desc = desc # Only for seperators.
        self.help = re.sub(r'\s+', ' ', h) if h else None
        self.num_params = int(p or 0)

    def print(self, *args):
        print(self.format(*args))


class Seperator(Action):
    pass

class MelAction(Action):

    def format(self, *args):
        return re.sub(r'%(\d+)', lambda m: str(args[int(m.group(1)) - 1]), self.source)

    def __call__(self, *args):
        from maya import mel
        mel.eval(self.format(*args))


class PythonAction(Action):

    def format(self):
        return self.source

    def __call__(self):

        source = self.source.strip()

        locals_ = {}
        eval(self.source, locals_)


class PythonEntryPointAction(Action):

    def format(self):
        return self.source

    def __call__(self):
        
        func, args, kwargs = load_entry_point(self.source.strip(), with_args=True)
        func(*args, **kwargs)


class AttrAction(Action):

    def __init__(self, **kw):
        super(AttrAction, self).__init__(p=1, **kw)

    def format(self, value):
        return 'setAttr {} {}'.format(self.source, value)

    def __call__(self, value):
        from maya import cmds
        if value.isdigit():
            value = int(value)
        cmds.setAttr(self.source, value)


class AttrStringAction(AttrAction):
    pass


class Renderer(object):

    def __init__(self, name):

        self.actions = {}
        self.ordered = []

        descriptor_path = find_descriptor(name)
        xml = etree.parse(descriptor_path)
        root = xml.getroot()

        '''The whole format:

        Top level tag, mandatory:
                <renderer>: "desc" gives a one line description.

          Header tags, not mandatory, must be specified only once.
            <melheader>: "s" is a mel script executed just after the file is read 
            <meltrailer>: "s" is a mel script executed after all flags are converted
                to mel. Should contain at least the rendering command.

          Other tags:
            <sep>: "desc" produces a line in the help. Blank if desc is missing.
            <attr>: produces a setAttr line.
                "n" is the flag name.
                "s" the attribute name.
                "t" the parameter type, used in help description.
                "h" the help description.
            <attrString>: produces a setAttr line for a string attribute.
                Same parameters as <attr>, but for string attributes.
            <mel>: Calls a mel script.
                "n" is the flag name.
                "p" the number of parameters.
                "s" the string defining the action %1 ... %p are replaced with values
                        read after the flag.
                "t" the parameter types, used in help description.
                "h" the help description.

        '''

        for node in root:

            if node.tag in ('mel', 'melheader', 'meltrailer'):
                action = MelAction.from_node(node)
            elif node.tag in ('attr', ):
                action = AttrAction.from_node(node)
            elif node.tag == 'attrString':
                action = AttrStringAction.from_node(node)
            elif node.tag in ('sep', ):
                action = Seperator.from_node(node)
            else:
                raise ValueError("Unknown node type {!r}.".format(node.tag))

            if action.name:
                self.actions[action.name] = action
            self.ordered.append(action)

    def __getitem__(self, name):
        return self.actions[name]

    def print_help(self):
        max_len = max(len(a.name) if a.name else 0 for a in self.ordered)
        for action in self.ordered:
            if action.desc:
                print()
                print(action.desc)
            if action.name or action.help:
                print('{:{}s} {}'.format(action.name, max_len, action.help or ''))

    def split_args(self, args):

        options = []
        while args and args[0].startswith('-') and args[0].lstrip('-') in self:
            name = args.pop(0).lstrip('-')
            action = self[name]
            params = args[:action.num_params]
            options.append((action, params))

        return options, args



if __name__ == '__main__':

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--renderer', default='default')
    args = parser.parse_args()

    renderer = Renderer(args.renderer)

    renderer['__init__'].print()
    renderer['x'].print(1024)
    renderer['fnc'].print('name.#.ext')
    renderer['__main__'].print()

