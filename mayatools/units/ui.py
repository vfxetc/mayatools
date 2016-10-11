from uitools.qt import Qt, QtCore, QtGui
import mayatools.units as units


unit_to_fps = {
    'sec (1 fps)': 1,
    'game (15 fps)': 15, 
    'film (24 fps)': 24, 
    'pal (25 fps)': 25, 
    'ntsc (30 fps)': 30, 
    'show (48 fps)': 48,  
    'palf (50 fps)': 50, 
    'ntscf (60 fps)': 60,
    'millisec (1000 fps)': 1000,
       '2 fps': 2, 
       '3 fps ': 3, 
       '4 fps': 4, 
       '5 fps': 5, 
       '6 fps': 6, 
       '8 fps': 8, 
       '10 fps': 10, 
       '12 fps': 12, 
       '16 fps': 16, 
       '20 fps': 20, 
       '40 fps': 40, 
       '75 fps': 75,
       '80 fps': 80, 
       '100 fps': 100, 
       '120 fps': 120, 
       '125 fps': 125, 
       '150 fps': 150, 
       '200 fps': 200,
       '240 fps': 240, 
       '250 fps': 250, 
       '300 fps': 300, 
       '375 fps': 375, 
       '400 fps': 400, 
       '500 fps': 500, 
       '600 fps': 600, 
       '750 fps': 750, 
       '1200 fps': 1200, 
       '1500 fps': 1500, 
       '2000 fps': 2000, 
       '3000 fps': 3000,
       '6000 fps': 6000
}





class MyDialog(QtGui.QDialog):

    def __init__(self):
        super(MyDialog, self).__init__()
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)

        self.set_fps = QtGui.QComboBox(self)
        layout.addWidget(self.set_fps)
        
        for name, fps in unit_to_fps.iteritems():
            if fps == units.core.get_fps():
                self.set_fps.addItem(name)


        for item in sorted(unit_to_fps, key=unit_to_fps.get):
            self.set_fps.addItem(item)

        self._ok_button = QtGui.QPushButton('Set')
        self._ok_button.clicked.connect(self._on_ok_clicked)
        layout.addWidget(self._ok_button)

        self._cancel_button = QtGui.QPushButton('Cancel')
        self._cancel_button.clicked.connect(self._on_cancel_clicked)
        layout.addWidget(self._cancel_button)

    def _on_cancel_clicked(self):
        self.close()

    def _on_ok_clicked(self):
        current_key = self.set_fps.currentText()
        current_value = unit_to_fps[current_key]
        units.core.set_fps(current_value)
        print units.core.get_fps()
        self.close()

dialog = None

def run():
    
    # Hold onto a reference so that it doesn't automatically close.
    global dialog
    
    if dialog:
        dialog.close()
    
    dialog = MyDialog()
    dialog.show()
    