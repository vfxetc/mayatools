from __future__ import absolute_import

# All imports should be in a function so that they do not polute the global
# namespace, except for `from maya import cmds` because we want that everywhere.
from maya import cmds, mel, OpenMaya


def standard_setup():
    """Non-standalone user setup."""
    
    import os
    import tempfile
    import datetime
    import sys

    base = '/var/tmp/maya.%s' % os.getpid()

    sock1 = base + '.cmdsock'
    try:
        import remotecontrol.server.maya
    except ImportError:
        cmds.warning('Could not import remotecontrol.server.maya.')
    else:
        if os.path.exists(sock1):
            os.unlink(sock1)
        remotecontrol.server.maya.spawn(sock1)

    sock2 = base + '.pysock'
    try:
        import remotecontrol.interpreter.maya
    except ImportError:
        cmds.warning('Could not import remotecontrol.interpreter.maya.')
    else:
        if os.path.exists(sock2):
            os.unlink(sock2)
        remotecontrol.interpreter.maya.spawn(sock2)


    # Tear it down later. (This only seems to work in 2013.)
    def close_command_port():

        try:
            if os.path.exists(sock1):
                os.unlink(sock1)
        except Exception as e:
            sys.__stdout__.write('%s while unlinking %s: %s\n' % (e.__class__.__name__, sock1, e))

        try:
            if os.path.exists(sock2):
                os.unlink(sock2)
        except Exception as e:
            sys.__stdout__.write('%s while unlinking %s: %s\n' % (e.__class__.__name__, sock2, e))
    
    cmds.scriptJob(event=('quitApplication', close_command_port))


# Block from running the production userSetup if the dev one already ran.
if not globals().get('__mayatools_usersetup__'):
    __mayatools_usersetup__ = True

    # Most things should not run in batch mode.
    if not cmds.about(batch=True):
        standard_setup()


# Cleanup the namespace.
del standard_setup
