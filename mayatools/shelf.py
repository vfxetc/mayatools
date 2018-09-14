from __future__ import absolute_import

import os
import re
import copy

import yaml

from maya import cmds, mel

from .tickets import ticket_ui_context
from .menus import setup_menu
from . import utils


# Need somewhere to hold the button definitions so that buttons may update
# themselves later.
_uuid_to_buttons = {}


    

def dispatch(entrypoint, args=(), kwargs={}, reload=None):
    with ticket_ui_context():
        func = utils.resolve_entrypoint(entrypoint, reload=reload)
        return func(*args, **kwargs)


def _iter_buttons(path, include_dirs, _visited=None):
    """Recursive iterator across the buttons in a path, respecting includes."""
    
    # Stop infinite recursion.
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

            for dir_ in include_dirs:
                path = os.path.join(dir_, button['include'])
                if os.path.exists(path):
                    break
            else:
                raise ValueError("Could not find included file.", button['include'])

            # Pass a copy of the visited set so that there is no recursion, but
            # we are able to include the same thing (e.g. a spacer) twice.
            for x in _iter_buttons(path, include_dirs, set(_visited)):
                yield x

        else:
            yield button



def get_top_shelf_layout():
    try:
        return get_top_shelf_layout._cached
    except AttributeError:
        get_top_shelf_layout._cached = x = mel.eval('$tmp=$gShelfTopLevel')
        return x


def load(shelf_dirs=None, image_dirs=None):
    
    # Default to $MAYA_SHELF_PATH.
    if shelf_dirs is None:
        shelf_dirs = os.environ.get('MAYA_SHELF_PATH')
        shelf_dirs = shelf_dirs.split(':') if shelf_dirs else []
    
    # Single strings should be a list.
    if isinstance(shelf_dirs, basestring):
        shelf_dirs = [shelf_dirs]
    
    # Clear out the button memory.
    _uuid_to_buttons.clear()
    
    # Lookup the tab shelf that we will attach to.
    layout = get_top_shelf_layout()
    
    # Store shelf options for restoring later.
    existing_options = {}
    for i, name in enumerate(cmds.shelfTabLayout(layout, q=True, childArray=True)):
        if name in existing_options:
            cmds.warning('Multiple shelves with name "%s"? This may cause problems.' % name)
        existing_options[name] = opts = {}
        for key in 'Name', 'File', 'Load':
            opts[key] = cmds.optionVar(q="shelf%s%d" % (key, i + 1))

    new_shelves = set()
    image_dirs = image_dirs or ()

    # Collect all shelves, and sort them by basename so no shelf directory
    # gets priority.
    shelf_paths = []
    for shelf_dir in shelf_dirs:
        try:
            file_names = os.listdir(shelf_dir)
        except IOError:
            continue
        for file_name in file_names:
            if file_name.startswith('.') or file_name.startswith('_') or not file_name.endswith('.yml'):
                continue
            shelf_paths.append(os.path.join(shelf_dir, file_name))
    shelf_paths.sort(key=os.path.basename)


    for shelf_path in shelf_paths:
        
        shelf_dir, file_name = os.path.split(shelf_path)
        shelf_name, ext = os.path.splitext(file_name)

        if shelf_name in new_shelves:
            continue

        new_shelves.add(shelf_name)
        print '# %s: %s' % (__name__, shelf_name)
        
        _load_shelf(shelf_path, shelf_dirs, image_dirs)

    # Clean up persistant shelf options; Maya (and plugins) will freak out at us if we don't.
    for i, name in enumerate(cmds.shelfTabLayout(layout, q=True, childArray=True)):
        if name in new_shelves:
            cmds.optionVar(stringValue=(("shelfName%d" % (i + 1)), name))
            cmds.optionVar(stringValue=(("shelfFile%d" % (i + 1)), ''))
            cmds.optionVar(intValue=(("shelfLoad%d" % (i + 1)), 1)) # Signal that it is loaded.
            continue
        opts = existing_options.get(name)
        if opts:
            cmds.optionVar(stringValue=(("shelfName%d" % (i + 1)), opts['Name']))
            cmds.optionVar(stringValue=(("shelfFile%d" % (i + 1)), opts['File']))
            cmds.optionVar(intValue=(("shelfLoad%d" % (i + 1)), opts['Load']))
            continue
        cmds.warning('New shelf "%s" appeared.' % name)

    cmds.optionVar(intValue=('numShelves', i + 1))

    # Finally, we need to save them all to the users' home. If we don't, and
    # another plugin (e.g. RenderMan) saves its own shelf, then on reload that
    # will be the only shelf which exists.
    cmds.saveAllShelves(layout)


def _load_shelf(shelf_path, shelf_dirs, image_dirs):

    shelf_name = os.path.splitext(os.path.basename(shelf_path))[0]
    layout = get_top_shelf_layout()

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

    for b_i, button in enumerate(_iter_buttons(shelf_path, shelf_dirs)):
    
        _load_button(copy.deepcopy(button), image_dirs)


def _load_button(button, image_dirs):

    # Defaults and basic setup.
    button.setdefault('width', 34)
    button.setdefault('height', 34)

    # Extract keys to remember buttons.
    uuids = [button.get('entrypoint'), button.pop('uuid', None)]
    
    # Extract other commands.
    doubleclick = button.pop('doubleclick', None)
    popup_menu = button.pop('popup_menu', None)
    context_menu = button.pop('context_menu', None)
    
    convert_entrypoints(button)

    # Find icons
    image_name = button.get('image')
    if image_name and not os.path.exists(image_name):
        for image_root in image_dirs:
            image_path = os.path.join(image_root, image_name)
            if os.path.exists(image_path):
                button['image'] = image_path
                break
        else:
            print 'Could not find button image:', image_name

    # Create the button!
    try:
        button['name'] = button_name = cmds.shelfButton(**button)
    except TypeError:
        print button
        raise

    # Save the button for later.
    for uuid in uuids:
        if uuid:
            _uuid_to_buttons.setdefault(uuid, []).append(button)
    
    # Add a doubleclick action if requested.
    if doubleclick:
        
        convert_entrypoints(doubleclick)
        
        # Only pass through the two keywords that are allowed.
        doubleclick = dict((k, v) for k, v in doubleclick.iteritems() if k in ('command', 'sourceType'))
        
        # Adapt to a doubleclick.
        doubleclick['doubleClickCommand'] = doubleclick.pop('command')
        
        cmds.shelfButton(button_name, edit=True, **doubleclick)
    
    # Add a popup menu if requested.
    if popup_menu:
        setup_menu(shelf_button=button_name, button=1, **popup_menu)
    if context_menu:
        setup_menu(shelf_button=button_name, button=3, **context_menu)



def buttons_from_uuid(uuid):
    return list(_uuid_to_buttons.get(uuid, []))


def convert_entrypoints(button):

    # Convert entrypoints into `dispatch` calls.
    if 'entrypoint' in button:
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
    """Usable as a button in Maya to reload the shelves."""
    
    # Must be done in the normal event loop since replacing reload button while
    # it is being called results in 2013 crashing.
    cmds.scriptJob(idleEvent=load, runOnce=True)


def test_exception_button(type_expr=None):
    type_ = eval(type_expr) if type_expr else RuntimeError
    raise type_("This is an expected failure.")


