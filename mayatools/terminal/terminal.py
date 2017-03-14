import sys
from maya import cmds

dialog = None


def run():
    
	path = cmds.file(q=True, sceneName=True) or '<UNSAVED>'
	print 'The current scene is:'
	print path

	print >> sys.__stdout__, 'The current scene is:',
	print >> sys.__stdout__, path
