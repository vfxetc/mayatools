import sys
from maya import cmds
import os

'''
The PID (via os.getpid())
- the current scene (via cmds.file(q=True, sceneName=True) or '<UNSAVED>')
- the current workspace
- a short random string (via os.urandom(4).encode('hex'))
'''

def run():
    
    path = cmds.file(q=True, sceneName=True) or '<UNSAVED>'
    nonce = os.urandom(4).encode('hex')

    msg = '\n'.join((
        '=== WHICH MAYA ===',
        'scene:      %s' % path,
        'workspaces: %s' % ', '.join(cmds.workspace(listWorkspaces=True)),
        'PID:        %s' % os.getpid(),
        'nonce:      %s' % nonce,
        '------------------',
    ))

    print msg
    print >> sys.__stdout__, msg
    
    # Short form.
    cmds.warning('Maya %d (%s) working on %s' % (
        os.getpid(),
        nonce,
        path,
    ))