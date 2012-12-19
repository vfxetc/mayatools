from __future__ import absolute_import

import sys
from unittest import TestCase as BaseTestCase

from uitools import trampoline
from uitools.trampoline import bounce, sleep, qpath

from mayatools.test import requires_maya


try:
    from PyQt4 import QtCore, QtGui
    Qt = QtCore.Qt
except ImportError:
    pass

try:
    from maya import cmds
except ImportError:
    class Stub(object):
        cmds = None
        utils = None
        standalone = None
    maya = Stub()
    sys.modules['maya'] = maya
    sys.modules['maya.cmds'] = None
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
        


