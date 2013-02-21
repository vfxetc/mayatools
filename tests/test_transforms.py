from common import *

from mayatools.transforms import transfer_global_transforms


class TestTransformBaking(TestCase):

    def test_basics(self):

        parent = cmds.spaceLocator(name='parentLocator')[0]
        child = cmds.spaceLocator(name='childLocator')[0]
        cmds.parent(child, parent)

        cmds.setKeyframe(parent, at='tx', time=1, v=1)
        cmds.setKeyframe(parent, at='tx', time=10, v=10)
        cmds.setKeyframe(child, at='ty', time=1, v=1)
        cmds.setKeyframe(child, at='ty', time=10, v=10)

        locator = cmds.spaceLocator(name='globalLocator')[0]

        transfer_global_transforms({locator: child})

        cmds.delete(parent, child)

        # Check the keyframes.
        self.assertEqual(cmds.getAttr(locator + '.tx', time=1), 1)
        self.assertEqual(cmds.getAttr(locator + '.ty', time=1), 1)
        self.assertEqual(cmds.getAttr(locator + '.tx', time=10), 10)
        self.assertEqual(cmds.getAttr(locator + '.ty', time=10), 10)

        # Interpolated.
        self.assertTrue(abs(cmds.getAttr(locator + '.tx', time=5) - 5) < 0.0001)
        self.assertTrue(abs(cmds.getAttr(locator + '.ty', time=5) - 5) < 0.0001)


