import os
import sys
import optparse


def run_remote(working_dir, argv, sys_path=None):

    old_modules = set(sys.modules)

    old_working_dir = os.getcwd()
    os.chdir(working_dir)

    # Extend the path so we can find nose.
    if sys_path:
        sys.path[:0] = sys_path

    import nose.core
    
    try:
        nose.core.main(argv=argv)
    except SystemExit:
        pass
        # Nope!
    finally:
        os.chdir(old_working_dir)
        for name in sorted(sys.modules):
            if name in old_modules:
                continue
            print '# Cleanup', name
            del sys.modules[name]


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
        remote('mayatools.test:run_remote', os.getcwd(), sys.argv[1:], [nose_path])

    else:

        interpreter = os.environ.get('MAYA_PYTHON', 'maya%s_python' % opts.version)

        environ = dict(os.environ)
        path = os.environ.get('PYTHONPATH')
        path = nose_path + (':' if path else '') + path
        environ['PYTHONPATH'] = path

        os.execvpe(interpreter, [interpreter, '-m', 'nose.core'] + sys.argv[1:], environ)
