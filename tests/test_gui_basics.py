from common import *


class TestGuiBasics(TestCase):

    @requires_maya(gui=True)
    def test_msgbox(self):

        msgbox = QtGui.QMessageBox()
        msgbox.setText("This should go away in 1 second.")
        msgbox.show()
        msgbox.raise_()

        sleep(1)

        buttons = qpath(msgbox, '//QPushButton', 0)
        
        try:
            self.assertTrue(buttons)
        finally:
            msgbox.close()



