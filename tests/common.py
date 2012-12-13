from unittest import TestCase as BaseTestCase

import maya.standalone
from maya import cmds


if not hasattr(cmds, 'sphere'):
    maya.standalone.initialize()



class TestCase(BaseTestCase):
    
    def setUp(self):
        cmds.file(new=True, force=True)


