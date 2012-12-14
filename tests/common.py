from __future__ import absolute_import

from unittest import TestCase as BaseTestCase

from uitools import trampoline
from mayatools.test import requires_maya


try:
    from maya import cmds
except ImportError:
    has_maya = False
else:
    has_maya = True


class TestCase(BaseTestCase):
    
    def setUp(self):
        cmds.file(new=True, force=True)


