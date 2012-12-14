from __future__ import absolute_import

import os
import sys
import optparse
import functools

try:
    import maya.cmds as maya_cmds
except ImportError:
    _has_maya = False
else:
    _has_maya = maya_cmds is not None

from uitools import trampoline

from . import threads


def requires_maya(func=None, gui=False):

    # Function as a decorator constructor.
    if not func:
        return functools.partial(requires_maya, gui=gui)

    # Start it up.
    if _has_maya and not hasattr(maya_cmds, 'about'):
        from maya import standalone
        standalone.initialize()

    if not _has_maya or (gui and maya_cmds.about(batch=True)):
        @functools.wraps(func)
        def _skipper(*args, **kwargs):
            from nose.exc import SkipTest
            raise SkipTest
        return _skipper

    # Not in batch mode, so we need to run in the main thread.
    if not maya_cmds.about(batch=True):
        trampoliner = trampoline.decorate(threads.call_in_main_thread)
        return trampoliner(func)

    # Pass it through.
    return func


def run(working_dir=None, argv=None, sys_path=None):

    old_modules = set(sys.modules)

    if working_dir is not None:
        old_working_dir = os.getcwd()
        os.chdir(working_dir)

    # Extend the path so we can find nose.
    if sys_path:
        sys.path[:0] = sys_path

    import nose.core
    
    try:
        nose.core.main(argv=['nosetests'] + list(argv or []))
    except SystemExit:
        pass
        # Nope!
    finally:
        if working_dir is not None:
            os.chdir(old_working_dir)
        cleaned = 0
        for name in sorted(sys.modules):
            if name in old_modules:
                continue
            cleaned += int(bool(sys.modules.pop(name, None)))
        if cleaned:
            print 'Unloaded %d modules.' % cleaned


if __name__ == '__main__':

    # Find nose.
    import nose
    nose_path = os.path.dirname(os.path.dirname(nose.__file__))

    opt_parser = optparse.OptionParser()
    opt_parser.add_option('-r', '--remote', action='store_true', dest='remote')
    opt_parser.add_option('--version', type='int', dest='version', default=2011)
    opts, args = opt_parser.parse_args()

    if opts.remote:

        test_dir = os.path.abspath(os.path.join(__file__, '..', '..'))

        from remotecontrol.client import open as open_remote
        remote = open_remote(unix_glob='/var/tmp/maya.*.cmdsock')
        remote.call('mayatools.test:run', (os.getcwd(), args, [nose_path]), main_thread=False)

    else:

        interpreter = os.environ.get('MAYA_PYTHON', 'maya%s_python' % opts.version)

        environ = dict(os.environ)
        path = os.environ.get('PYTHONPATH')
        path = nose_path + (':' if path else '') + path
        environ['PYTHONPATH'] = path

        os.execvpe(interpreter, [interpreter, '-m', 'nose.core'] + args, environ)
