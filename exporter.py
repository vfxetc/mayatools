from __future__ import absolute_import

from PyQt4 import QtCore, QtGui
Qt = QtCore.Qt

from maya import cmds

from ks.core.scene_name.widget import SceneNameWidget


class CacheSelector(QtGui.QWidget):

    def __init__(self, name):
        super(CacheSelector, self).__init__()
        self._name = name
        self._setup_ui()
    
    def _setup_ui(self):
        
        self.setLayout(QtGui.QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        
        self._checkbox = QtGui.QCheckBox()
        self._checkbox.stateChanged.connect(self._on_checkbox)
        self.layout().addWidget(self._checkbox)
        
        self._label = QtGui.QLabel(self._name)
        self.layout().addWidget(self._label)
        
        self.layout().addStretch()
        
        self._edit = QtGui.QLineEdit(self._name)
        self._edit.setFixedSize(QtCore.QSize(200, self._edit.sizeHint().height()))
        self.layout().addWidget(self._edit)
        
        self._on_checkbox()
    
    def _on_checkbox(self, *args):
        self._edit.setEnabled(self._checkbox.isChecked())
        

class Dialog(QtGui.QDialog):

    def __init__(self):
        super(Dialog, self).__init__()
        
        self._init_ui()
    
    def _init_ui(self):
        self.setLayout(QtGui.QVBoxLayout())
        
        area = self._sets_area = QtGui.QScrollArea()
        area.setWidgetResizable(True)
        self.layout().addWidget(area)
        frame = self._sets_frame = QtGui.QWidget()
        area.setWidget(frame)
        frame.setLayout(QtGui.QVBoxLayout())
        
        self._selectors = []
        for set_ in cmds.ls(sets=True) + [str(i) for i in range(10)]:
            self._selectors.append(CacheSelector(set_))
        for selector in self._selectors:
            frame.layout().addWidget(selector)
        if not self._selectors:
            frame.layout().addWidget(QtGui.QLabel("Nothing to cache."), alignment=Qt.AlignHCenter)
        frame.layout().addStretch()
        
        box = self._scene_name_box = QtGui.QGroupBox()
        box.setLayout(QtGui.QVBoxLayout())
        self.layout().addWidget(box)
    
        self._scene_name = SceneNameWidget(dict(
            scenes_name='data/geoCache',
            sub_directory='',
            workspace=cmds.workspace(q=True, rd=True),
        ))
        box.layout().addWidget(self._scene_name)
    
        button_layout = QtGui.QHBoxLayout()
        self.layout().addLayout(button_layout)
    
        button = self._save_button = QtGui.QPushButton("Save Settings")
        button.setFixedSize(QtCore.QSize(100, button.sizeHint().height()))
        button_layout.addWidget(button)

        button_layout.addStretch()
        
        button = self._local_button = QtGui.QPushButton("Process Locally")
        button.setFixedSize(QtCore.QSize(100, button.sizeHint().height()))
        button_layout.addWidget(button)
        
        button = self._qube_button = QtGui.QPushButton("Queue on Farm")
        button.setFixedSize(QtCore.QSize(100, button.sizeHint().height()))
        button_layout.addWidget(button)
        
        
        
def __before_reload__():
    if dialog:
        dialog.close()

dialog = None

def run():
    
    global dialog
    
    if dialog:
        dialog.close()
    
    dialog = Dialog()    
    dialog.show()
