"""Context managers for Maya state."""

import contextlib
import functools


try:
    from maya import cmds
except ImportError:
    # For Sphinx.
    cmds = None


@contextlib.contextmanager
def attrs(*args, **kwargs):
    """Change some attributes, and reset them when leaving the context.
    
    :param args: Mappings of attributes to values.
    :param kwargs: More attributes and values.
    :returns: A dictionary of the original values will be bound to the target of
        the with statement. Changed to that dictionary will be applied.
    
    Useful for playblasting::
    
        >>> with mayatools.context.attrs({'defaultRenderGlobals.imageFormat': 8}):
        ...     # Playblast with confidence that the render globals will be reset.
    
    """
    
    # Collect all the arguments.
    for arg in args:
        kwargs.update(arg)
    
    existing = {}
    try:
        
        # Set all of the requested attributes.
        for name, value in kwargs.iteritems():
            existing[name] = cmds.getAttr(name)
            cmds.setAttr(name, value)
        
        yield existing
    
    finally:
        
        # Reset them back to normal.
        for name, value in existing.iteritems():
            cmds.setAttr(name, value)


def edit(func, *args, **kwargs):
    """A context manager that uses the standard query/edit interface.
    
    Pass any values via keyword arguments and their original values will be
    saved via ``func(*args, query=True, yourAttribute=True)``, and finally
    restored via ``func(*args, edit=True, yourAttribute=original)``.
    
    :param func: A callable, or name of a Maya command.
    :param args: Positional arguments for the given ``func``.
    :param kwargs: Values to set within the context.
    
    A dictionary of the original values will be bound to the target of the with
    statement. Changed to that dictionary will be applied.
    
    If you are already using a query/edit pattern like::
    
        >>> original_overscan = cmds.camera(my_object, query=True, overscan=True)
        >>> cmds.camera(my_object, edit=True, overscan=1)
        >>> 
        >>> try:
        ...     # Do something.
        ... finally:
        ...     cmds.camera(my_object, edit=True, overscan=original_overscan)
    
    then you can use this manager directly::
    
        >>> with edit(cmds.camera, my_object, overscan=1) as originals:
        ...     # Do something.
    
    or as a context manager factory::
    
        >>> camera = edit(cmds.camera)
        >>> with camera(my_object, overscan=1) as originals:
        ...     # Do something.
    
    """
    
    if kwargs:
        return _edit(func, {'edit': True}, *args, **kwargs)
    else:
        return functools.partial(_edit, func, {'edit': True}, *args)


def command(func, *args, **kwargs):
    """A context manager that uses the standard query interface.
    
    Pass any values via keyword arguments and their original values will be
    saved via ``func(*args, query=True, yourAttribute=True)``, and finally
    restored via ``func(*args, yourAttribute=original)``.
    
    :param func: A callable, or name of a Maya command.
    :param args: Positional arguments for the given ``func``.
    :param kwargs: Values to set within the context.
    
    A dictionary of the original values will be bound to the target of the with
    statement. Changed to that dictionary will be applied.
    
    If you are already using a query pattern like::
    
        >>> current_time_unit = cmds.currentUnit(time)
        >>> cmds.currentUnit(time='film')
        >>> 
        >>> try:
        ...     # Do something.
        ... finally:
        ...     cmds.currentUnit(time=current_time_unit)
    
    then you can use this manager directly::
    
        >>> with command(cmds.currentUnit, time='film') as originals:
        ...     # Do something.
    
    or as a context manager factory::
    
        >>> currentUnit = command(cmds.currentUnit)
        >>> with currentUnit(time='film') as originals:
        ...     # Do something.
    
    """
    if kwargs:
        return _edit(func, {}, *args, **kwargs)
    else:
        return functools.partial(_edit, func, {}, *args)


@contextlib.contextmanager
def _edit(func, edit_kwargs, *args, **kwargs):
        
    if isinstance(func, basestring):
        func = getattr(cmds, func)
        
    existing = {}
    try:
            
        # Set the requested parameters.
        for name, value in kwargs.iteritems():
            existing[name] = func(*args, query=True, **{name: True})
            set_kwargs = edit_kwargs.copy()
            set_kwargs[name] = value
            func(*args, **set_kwargs)
            
        yield existing
        
    finally:
            
        # Reset them back to normal.
        for name, value in existing.iteritems():
            set_kwargs = edit_kwargs.copy()
            set_kwargs[name] = value
            func(*args, **set_kwargs)
    

@contextlib.contextmanager
def selection(*args, **kwargs):
    """A context manager that resets selections after exiting.

    :param args: Passed to ``cmds.select``.
    :param kwargs: Passed to ``cmds.select``.
    
    A list of the original selection will be bound to the target of the with
    statement. Changes to that list will be applied.
    
    Example::
    
        >>> with selection(clear=True):
        ...     # Do something with an empty selection.
    
    """
    existing = cmds.ls(selection=True) or []
    try:
        if args or kwargs:
            cmds.select(*args, **kwargs)
        yield existing
    finally:
        if existing:
            cmds.select(existing, replace=True)
        else:
            cmds.select(clear=True)
    












