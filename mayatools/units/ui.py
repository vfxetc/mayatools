from uitools.qt import Qt, QtCore, QtGui
import mayatools.units as units

dialog = None
unit_to_fps = {}
temp_list = []

temp_list = list(units.core.valid_fpses)

for item in units.core.fps_to_unit:
    if item in temp_list:
        temp_list.remove(item)

for item in temp_list:
    name = str(item) + " fps"
    unit_to_fps[name] = item

for item in units.core.unit_to_fps:
    name = item + " (" + str(units.core.unit_to_fps[item]) + " fps)"
    unit_to_fps[name] = units.core.unit_to_fps[item]





class MyDialog(QtGui.QDialog):

    def __init__(self):
        super(MyDialog, self).__init__()
        self._setup_ui()
    
    def _setup_ui(self):
        self.setWindowTitle('Set FPS')
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
              
        self._cancel_button = QtGui.QPushButton('Cancel')
        self._cancel_button.clicked.connect(self._on_cancel_clicked)
        
     
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(self._ok_button)
        hbox.addWidget(self._cancel_button)

        self.layout().addLayout(hbox)

    def _on_cancel_clicked(self):
        self.close()

    def _on_ok_clicked(self):
        current_key = self.set_fps.currentText()
        current_value = unit_to_fps[current_key]
        units.core.set_fps(current_value)
        print units.core.get_fps()
        self.close()



def run():
    
    # Hold onto a reference so that it doesn't automatically close.
    global dialog
    
    if dialog:
        dialog.close()
    
    dialog = MyDialog()
    dialog.show()
    