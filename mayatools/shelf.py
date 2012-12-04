from __future__ import absolute_import

import __builtin__
import os
import re
import sys
import time
import copy
import traceback

import yaml
import autoreload

from maya import cmds, mel

__also_reload__ = ['sgactions.ticketui']


def dispatch(entrypoint, args=(), kwargs={}, reload=None):
    
    parts = entrypoint.split(':')
    if len(parts) != 2:
        cmds.error('Entrypoint must look like "package.module:function"; got %r' % entrypoint)
        return
        
    module_name, attribute = parts
    
    # If we can't directly import it, then import the package and get the
    # module via attribute access. This is because of the `code` sub-package
    # on many of the older tools.
    try:
        module = __import__(module_name, fromlist=['.'])
    except ImportError, ie:
        parts = module_name.rsplit('.', 1)
        if len(parts) == 1:
            raise ie
        package_name, module_name = parts
        package = __import__(package_name, fromlist=['.'])
        try:
            module = getattr(package, module_name)
        except AttributeError:
            raise ie
    
    if reload or reload is None:
        did_reload = autoreload.autoreload(module)
        if reload and not did_reload:
            __builtin__.reload(module)
    
    try:
        func = getattr(module, attribute)
    except AttributeError:
        cmds.error('%r module has no %r attribute' % (module.__name__, attribute))
        return
    
    try:
        result = func(*args, **kwargs)
    except Exception as e:
        try:
            from sgactions.ticketui import handle_current_exception
        except ImportError:
            raise e
        else:
            if not handle_current_exception():
                raise e
            return None
    
    return result


def _iter_buttons(path, _visited=None):
    
    if _visited is None:
        _visited = set()
    if path in _visited:
        return
    _visited.add(path)
    
    serialized = open(path).read()
    buttons = yaml.load_all(serialized)
    for button in buttons:
        if not button:
            continue
        if 'include' in button:
            include_path = os.path.join(os.path.dirname(path), button['include'])
            # Pass a copy of the visited set so that there is no recursion, but
            # we are able to include the same thing (e.g. a spacer) twice.
            for x in _iter_buttons(include_path, set(_visited)):
                yield x
        else:
            yield button


if 'MAYA_SHELF_PATH' in os.environ:
    default_shelf_path = os.environ['MAYA_SHELF_PATH'].split(':')
else:
    default_shelf_path = []


_uuid_to_buttons = {}


def load(shelf_path=None):
    
    # Sort out shelf and icon directories.
    shelf_path = shelf_path or default_shelf_path
    if isinstance(shelf_path, basestring):
        shelf_path = [shelf_path]
    
    # Clear out the button memory.
    _uuid_to_buttons.clear()
    
    # Lookup the tab shelf that we will attach to.
    layout = mel.eval('$tmp=$gShelfTopLevel')
    
    shelf_names = set()
    
    for shelf_dir in shelf_path:
        try:
            file_names = sorted(os.listdir(shelf_dir))
        except IOError:
            continue
        for file_name in file_names:
            if file_name.startswith('.') or file_name.startswith('_') or not file_name.endswith('.yml'):
                continue
            
            shelf_name = file_name[:-4]
            shelf_names.add(shelf_name)
            print '# %s: %s' % (__name__, shelf_name)
        
            # Delete buttons on existing shelves, and create shelves that don't
            # already exist.
            if cmds.shelfLayout(shelf_name, q=True, exists=True):
                # Returns None if not loaded yet, so be careful.
                for existing_button in cmds.shelfLayout(shelf_name, q=True, childArray=True) or []:
                    cmds.deleteUI(existing_button)
                cmds.setParent(layout + '|' + shelf_name)
            else:
                cmds.setParent(layout)
                cmds.shelfLayout(shelf_name)
        
            for b_i, button in enumerate(_iter_buttons(os.path.join(shelf_dir, file_name))):
            
                raw_button = copy.deepcopy(button)
            
                # Defaults and basic setup.
                button.setdefault('width', 34)
                button.setdefault('height', 34)
            
                # Be able to track buttons.
                uuids = [button.get('entrypoint'), button.pop('uuid', None)]
            
                convert_entrypoints(button)
                doubleclick = button.pop('doubleclick', None)
            
                # Create the button!
                try:
                    raw_button['name'] = button_name = cmds.shelfButton(**button)
                except TypeError:
                    print button
                    raise
            
                # Save the button for later.
                for uuid in uuids:
                    if uuid:
                        _uuid_to_buttons.setdefault(uuid, []).append(raw_button)
            
                if doubleclick:
                    convert_entrypoints(doubleclick)
                    doubleclick = dict((k, v) for k, v in doubleclick.iteritems() if k in ('command', 'sourceType'))
                    doubleclick['doubleClickCommand'] = doubleclick.pop('command')
                    cmds.shelfButton(button_name, edit=True, **doubleclick)
    
    # Reset all shelf options; Maya will freak out at us if we don't.
    for i, name in enumerate(cmds.shelfTabLayout(layout, q=True, childArray=True)):
        if name in shelf_names:
            cmds.optionVar(stringValue=(("shelfName%d" % (i + 1)), shelf_name))


def buttons_from_uuid(uuid):
    return list(_uuid_to_buttons.get(uuid, []))


def convert_entrypoints(button):

    # Convert entrypoints into `dispatch` calls.
    if 'entrypoint' in button:
        kwargs = {}
        arg_specs = [repr(button.pop('entrypoint'))]
        for attr in 'args', 'kwargs', 'reload':
            if attr in button:
                arg_specs.append('%s=%r' % (attr, button.pop(attr)))
        button['python'] = 'from %s import dispatch; dispatch(%s)' % (
            __name__,
            ', '.join(arg_specs),
        )
            
    # Move convenience keys into "command".
    if 'python' in button:
        button['command'] = button.pop('python')
        button['sourceType'] = 'python'
    if 'mel' in button:
        button['command'] = button.pop('mel')
        button['sourceType'] = 'mel'
            
    # Don't let None commands escape into the Maya API.
    if 'command' in button and button['command'] is None:
        del button['command']

def dump(shelves=None, shelf_dir=None, image_dir=None):
    
    if shelf_dir is None:
        shelf_dir = os.path.abspath(os.path.join(__file__, '..', '..', 'shelf'))
    
    if image_dir is None:
        image_dir = os.path.abspath(os.path.join(__file__, '..', '..', 'icons'))
    
    attributes = dict(
        imageOverlayLabel='',
        annotation='',
        enableCommandRepeat=True,
        enable=True,
        width=set((32, 34, 35)),
        height=set((32, 34, 35)),
        manage=True,
        visible=True,
        preventOverride=False,
        align='center',
        label='',
        labelOffset=0,
        font='plainLabelFont',
        image='',
        style='iconOnly',
        marginWidth=1,
        marginHeight=1,
        command='',
        sourceType='',
        actionIsSubstitute=False,
    )

    layout = mel.eval('$tmp=$gShelfTopLevel')
    
    if shelves is None:
        shelves = cmds.shelfTabLayout(layout, q=True, childArray=True)
    elif isinstance(shelves, basestring):
        shelves = [shelves]
    
    for shelf in shelves:
        
        buttons = cmds.shelfLayout(shelf, q=True, childArray=True)
        if not buttons:
            print '# Shelf not loaded:', shelf
            continue
        
        path = os.path.join(shelf_dir, shelf) + '.yml'
        with open(path, 'w') as file:
            
            for button in buttons:
                print shelf, button
                
                data = dict()
                for attr, default in attributes.iteritems():
                    value = cmds.shelfButton(button, q=True, **{attr: True})
                    if isinstance(value, basestring):
                        value = str(value)
                    if value != default and not (isinstance(default, set) and value in default):
                        data[attr] = value
                
                # Convert images to icon names.
                image = data.pop('image', '')
                if image:
                    if image.startswith(image_dir):
                        image = image[len(image_dir):].strip('/')
                    data['image'] = image
                
                type_ = data.pop('sourceType')
                data[type_] = data.pop('command', None)
                if type_ == 'python':
                    source = data.pop('python')
                    # from key_core import key_ui;reload(key_ui);key_ui.saveSelectedWin()
                    if source:
                        m = re.match(r'^from ([\w.]+) import (\w+) (?:;|,|\n) (?:reload\(\2\) (?:;|,|\n))? \2.(\w+)\(\) ;?$'.replace(' ', r'\s*'), source)
                        if m:
                            data['entrypoint'] = '%s.%s:%s' % m.groups()
                            if 'reload(' in source:
                                data['reload'] = True
                            source = None
                    if source:
                        m = re.match(r'^from ([\w.]+) import (\w+) as \w+ (?:;|,|\n) (?:reload\(\w+\) (?:;|,|\n))? \w+.(\w+)\(\) ;?$'.replace(' ', r'\s*'), source)
                        if m:
                            data['entrypoint'] = '%s.%s:%s' % m.groups()
                            if 'reload(' in source:
                                data['reload'] = True
                            source = None
                    if source:
                        data['python'] = source
                    
                
                
                
                file.write(yaml.dump(data,
                    explicit_start=True,
                    indent=4,
                    default_flow_style=False,
                ))


def load_button():
    # Must be done in the normal event loop since replacing reload button while
    # it is being called results in 2013 crashing.
    cmds.scriptJob(idleEvent=load, runOnce=True)

def fail_button():
    raise ValueError("this is a test")
