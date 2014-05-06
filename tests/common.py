from __future__ import absolute_import

import sys
from unittest import TestCase as BaseTestCase

from uitools import trampoline
from uitools.qt import QtCore, QtGui, Qt
from uitools.trampoline import bounce, sleep, qpath

from mayatools.test import requires_maya

try:
    from maya import cmds, mel
except ImportError:
    class Stub(object):
        cmds = None
        mel = None
        utils = None
        standalone = None
    maya = Stub()
    sys.modules['maya'] = maya
    sys.modules['maya.cmds'] = None
    sys.modules['maya.mel'] = None
    sys.modules['maya.utils'] = None
    sys.modules['maya.standalone'] = None
    cmds = Stub()
    has_maya = False
else:
    has_maya = True


class TestCase(BaseTestCase):
    
    @requires_maya
    def setUp(self):
        cmds.file(new=True, force=True)
        


