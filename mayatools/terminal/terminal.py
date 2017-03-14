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
	print 'The current scene is:'
	print path
	print 'The current PID is:'
	print os.getpid()
	print 'The current workspace is:'
	print cmds.workspace(listWorkspaces=True )

	print 'Random string is:'
	print os.urandom(4).encode('hex')

	print >> sys.__stdout__, 'The current scene is:',
	print >> sys.__stdout__, path
	print >> sys.__stdout__, 'The current PID is:', os.getpid()
	print >> sys.__stdout__, 'The current workspace is:'
	print >> sys.__stdout__, cmds.workspace(listWorkspaces=True )

	print >> sys.__stdout__, 'Random string is:', os.urandom(4).encode('hex')
