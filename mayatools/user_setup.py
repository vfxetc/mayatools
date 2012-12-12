from __future__ import absolute_import

# All imports should be in a function so that they do not polute the global
# namespace, except for `from maya import cmds` because we want that everywhere.
from maya import cmds, mel, OpenMaya


def standard_setup():
    """Non-standalone user setup."""
    
    import os
    import tempfile
    import time
    import sys

    # Create a commandPort.
    sock = tempfile.NamedTemporaryFile(prefix='maya.', suffix='.pysock', delete=False).name
    cmds.commandPort(name=sock, sourceType='python')
    print 'unix commandPort at %s' % sock

    # Tear it down later. (This only seems to work in 2013.)
    def close_command_port():

        try:
            cmds.commandPort(name=sock, close=True)
        except Exception as e:
            sys.__stdout__.write('%s while closing commandPort: %s\n' % (e.__class__.__name__, e))

        try:
            if os.path.exists(sock):
                os.unlink(sock)
        except Exception as e:
            sys.__stdout__.write('%s while unlinking commandPort socket: %s\n' % (e.__class__.__name__, e))
    
    cmds.scriptJob(event=('quitApplication', close_command_port))


# Block from running the production userSetup if the dev one already ran.
if not globals().get('__mayatools_usersetup__'):
    __mayatools_usersetup__ = True

    # Most things should not run in batch mode.
    if not cmds.about(batch=True):
        standard_setup()


# Cleanup the namespace.
del standard_setup
