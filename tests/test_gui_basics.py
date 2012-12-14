from common import *


class TestGuiBasics(TestCase):

    @requires_maya(gui=True)
    def test_msgbox(self):

        msgbox = QtGui.QMessageBox()
        msgbox.setText("This will go away in 1 second.")
        msgbox.show()
        msgbox.raise_()

        sleep(1)

        msgbox.close()



