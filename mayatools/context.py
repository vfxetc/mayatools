"""

Context managers for restoring state after running requested tools.

These are generally quite useful for creating tools which must modify state that
is normally under control of the user. By using these, the state will be set
back to what the user left it at.

For example, several of Maya's tools work easiest when they are operating on
the current selection, but that selection is not something that we want to
expose to the user of our higher level tool.

"""

import contextlib
import functools

from uitools.qt import QtGui, QtCore

from maya import cmds, mel


@contextlib.contextmanager
def attrs(*args, **kwargs):
    """Change some attributes, and reset them when leaving the context.
    
    :param args: Mappings of attributes to values.
    :param kwargs: More attributes and values.
    :returns: A dictionary of the original values will be bound to the target of
        the with statement. Changed to that dictionary will be applied.
    
    This is very for tools that must modify global state::
    
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


def command(func, *args, **kwargs):
    """A context manager that uses the standard query interface.
    
    Pass any values via keyword arguments and their original values will be
    saved via ``func(*args, query=True, yourAttribute=True)``, and finally
    restored via ``func(*args, yourAttribute=original)`` or
    ``func(*args, edit=True, yourAttribute=original)`` if you also specify
    ``edit=True``.
    
    :param func: A callable, or name of a Maya command.
    :param args: Positional arguments for the given ``func``.
    :param kwargs: Values to set within the context. ``edit`` is special and
        marks if values should be set with an ``edit`` flag or not.
    
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
    
    If your command requires the ``edit`` keyword, pass it to this function::
    
        >>> with ctx.command(cmds.camera, my_camera, edit=True, overscan=1):
        ...     # Do something with the camera.
    
    """
    if args or kwargs:
        return _command(func, *args, **kwargs)
    else:
        return functools.partial(_command, func)


@contextlib.contextmanager
def _command(func, *args, **kwargs):
        
    if isinstance(func, basestring):
        func = getattr(cmds, func)
    
    edit = bool(kwargs.pop('edit', None))
    
    existing = {}
    try:
            
        # Set the requested parameters.
        for name, value in kwargs.iteritems():
            existing[name] = func(*args, query=True, **{name: True})
            if edit:
                func(*args, edit=True, **{name: value})
            else:
                func(*args, **{name: value})
            
        yield existing
        
    finally:
            
        # Reset them back to normal.
        for name, value in existing.iteritems():
            if edit:
                func(*args, edit=True, **{name: value})
            else:
                func(*args, **{name: value})
    

@contextlib.contextmanager
def selection(*args, **kwargs):
    """A context manager that resets selections after exiting.

    :param args: Passed to ``cmds.select``.
    :param kwargs: Passed to ``cmds.select``.
    
    A list of the original selection will be bound to the target of the with
    statement. Changes to that list will be applied.
    
    Example::
    
        >>> with selection(clear=True):
        ...     # Do something with an empty selection, but restore the user's
        ...     # selection when we are done.
    
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
    

@contextlib.contextmanager
def delete(*to_delete, **kwargs):
    """A context manager that deletes nodes after exiting.

    :param args: Passed to ``cmds.delete``.
    :param kwargs: Passed to ``cmds.delete``.
    
    A list of the nodes to delete will be bound to the target of the with
    statement. Changes to that list will be applied.
    
    Example::
    
        >>> with delete() as to_delete:
        ...     # Create temporary nodes and register them in to_delete.

    This is useful when creating temporary nodes, and registering them for
    deletion after the context is exited, even if the process failed.
    
    """

    # Make it mutable.
    to_delete = list(to_delete)

    try:
        yield to_delete
    finally:
        if to_delete:
            cmds.delete(*to_delete)


_suspend_depth = 0

@contextlib.contextmanager
def suspend_refresh():
    """A context mananger that stops the graph from running or the view
    updating.

    Can be nested, where only the outermost context manager will resume
    refresing.

    ::

        >>> with suspend_refresh():
        ...     do_something_with_high_drawing_cost()


    .. seealso::

        There are caveats with disabling the refresh cycle. Be sure to 
        read about :cmds:`refresh`.

    """

    global _suspend_depth
    try:
        if not _suspend_depth:
            cmds.refresh(suspend=True)
        _suspend_depth += 1
        yield
    finally:
        _suspend_depth -= 1
        if not _suspend_depth:
            cmds.refresh(suspend=False)



class progress(object):
    """A context manager to assist with the global progress bar.

    :param str status: The status message.
    :param int max: The maximum value.
    :param int min: The minimum value.
    :param bool cancellable: If the process is cancellable.

    If the process is cancellable, you must periodically check
    :meth:`.was_cancelled` to see if the user did cancel the action. You must
    be more defensive in your programming than normal since this must allow the
    main event loop to process user events.

    ::

        with progress("Testing", max=100, cancellable=True) as p:
            for i in range(100):
                if p.was_cancelled():
                    cmds.warn('You cancelled the process!')
                    break
                time.sleep(0.02)
                p.update(i, 'Testing %d of 100' % (i + 1))

    """

    def __init__(self, status, max=100, min=0, cancellable=False):
        self._status = status
        self._min = min
        self._max = max
        self._cancellable = cancellable
        self._was_cancelled = False

    def step(self, size=1):
        """Increment the value."""
        cmds.progressBar(self._bar, edit=True, step=size)

    def update(self, value=None, status=None, min=None, max=None):
        """Update the value and status."""
        self._status = status or self._status
        self._min = min or self._min
        self._max = max or self._max
        kwargs = {'progress': value} if value is not None else {}
        cmds.progressBar(self._bar, edit=True,
            status=self._status,
            minValue=self._min,
            maxValue=self._max,
            **kwargs
        )

    def was_cancelled(self, max_time=0.01):
        """Check if the user requested the action be cancelled.

        :param float max_time: The maximum number of seconds to spend in the
            main event loop checking for user actions.
        :returns bool: True if the user requested the action be cancelled.

        """
        
        if not self._cancellable:
            return False

        if self._was_cancelled:
            return self._was_cancelled

        # Allow the main thread to process events for just a little bit so that
        # it may catch the escape key.
        QtGui.QApplication.instance().processEvents(QtCore.QEventLoop.ExcludeSocketNotifiers, max_time)

        self._was_cancelled = cmds.progressBar(self._bar, query=True, isCancelled=True)
        return self._was_cancelled

    def show(self):
        """Show the progress bar."""
        main_bar = mel.eval('$tmp = $gMainProgressBar')
        self._bar = cmds.progressBar(main_bar,
            edit=True,
            beginProgress=True,
            status=self._status,
            minValue=self._min,
            maxValue=self._max,
            isInterruptable=self._cancellable,
        )

    def hide(self):
        """Hide the progress bar."""
        cmds.progressBar(self._bar, edit=True, endProgress=True)

    def __enter__(self):
        self.show()
        return self

    def __exit__(self, *args):
        self.hide()



