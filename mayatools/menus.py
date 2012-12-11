import functools
import os

from PyQt4 import QtGui

from maya import cmds

from .qt import maya_to_qt
from .tickets import ticket_ui_context
from .utils import resolve_entrypoint


def setup_menu(shelf_button, button=1, dynamic=False, constructor=None, **kwargs):
    
    # Clear existing.
    existing = cmds.shelfButton(shelf_button, q=True, popupMenuArray=True) or []
    existing = [x for x in existing if cmds.popupMenu(x, q=True, button=True) == button]
    if existing:
        cmds.deleteUI(existing)
    
    cmds.popupMenu(
        parent=shelf_button,
        button=button,
        postMenuCommand=functools.partial(constructor_dispatch, **kwargs),
        postMenuCommandOnce=not dynamic,
    )


def constructor_dispatch(maya_menu, parent, constructor=None, **kwargs):
    with ticket_ui_context():
        constructor = resolve_entrypoint(constructor) if constructor else default_constructor
        constructor(maya_menu, **kwargs)


def default_constructor(maya_menu, actions=None):
    
    menu = maya_to_qt(maya_menu)
    
    res = []
    for spec in (actions or []):
        
        if spec.get('seperator'):
            menu.addSeparator()
            continue
        
        # We need to create the menu item via Maya, otherwise it doesn't work
        # on linux.
        maya_item = cmds.menuItem(parent=maya_menu, label=spec['label'], command=functools.partial(lambda *args, **spec: action_dispatch(**spec), **spec))
        action = maya_to_qt(maya_item)
        
        # Find an icon in the XBMLANGPATH, which is the same path that Maya
        # uses.
        if 'icon' in spec:
            base, ext = os.path.splitext(spec['icon'])
            name = base + (ext or '.png')
            if not os.path.isabs(name):
                for root in os.environ.get('XBMLANGPATH', '').split(':'):
                    path = os.path.join(root, name)
                    if os.path.exists(path):
                        break
                else:
                    path = name
            else:
                path = name
            action.setIcon(QtGui.QIcon(path))
        
        res.append(action)
    return res


def action_dispatch(entrypoint=None, python=None, **kwargs):
    with ticket_ui_context():
        if entrypoint is not None:
            func = resolve_entrypoint(entrypoint)
            func(*(kwargs.get('args') or ()), **(kwargs.get('kwargs') or {}))
        elif python is not None:
            eval(compile(python, '<menu action>', 'exec'), kwargs)
        else:
            raise RuntimeError('Need entrypoint or python for menu action; got %r' % sorted(kwargs))
