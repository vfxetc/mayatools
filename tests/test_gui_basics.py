from common import *


class TestGuiBasics(TestCase):

    @requires_maya(gui=True)
    def test_sleep(self):
        print 'And now, we sleep!'
        sleep(5)


