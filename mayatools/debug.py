"""

from metatools.imports import autoreload
from mayatools import debug
autoreload(debug)
debug.disable_verbose_commands()
debug.enable_verbose_commands()

cmds.about(version=True)

"""

import sys
import datetime
import thread

from maya import cmds


class CommandWrapper(object):

    def __init__(self, cmd):
        self.wrapped_cmd = cmd

    def __call__(self, *args, **kwargs):
        arg_spec = [repr(x) for x in args]
        arg_spec.extend('%s=%r' % (k, v) for k, v in sorted(kwargs.iteritems()))
        sys.__stderr__.write('%s %08x %s(%s)\n' % (
            datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),
            thread.get_ident(),
            self.wrapped_cmd.__name__,
            ', '.join(arg_spec),
        ))
        sys.__stdout__.flush()
        return self.wrapped_cmd(*args, **kwargs)


def enable_verbose_commands():
    for name, value in cmds.__dict__.items():
        if callable(value) and not hasattr(value, 'wrapped_cmd'):
            setattr(cmds, name, CommandWrapper(value))

def disable_verbose_commands():
    for name, value in cmds.__dict__.items():
        setattr(cmds, name, getattr(value, 'wrapped_cmd', value))
