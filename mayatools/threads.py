import thread
import threading
import sys

try:
    import maya.utils
except ImportError:
    pass


_locals = threading.local()
_wait_for_ident = threading.Condition()
_main_ident = None


def _get_main_ident():
    global _main_ident
    _main_ident = thread.get_ident()
    with _wait_for_ident:
        _wait_for_ident.notify()


def call_in_main_thread(func, *args, **kwargs):

    if _main_ident is None:
        with _wait_for_ident:
            maya.utils.executeDeferred(_get_main_ident)
            _wait_for_ident.wait()

    _locals.depth = getattr(_locals, 'depth', 0) + 1
    if _locals.depth <= 1 and _main_ident != thread.get_ident():
        res = maya.utils.executeInMainThreadWithResult(func, *args, **kwargs)
    else:
        res = func(*args, **kwargs)
    _locals.depth -= 1

    return res

