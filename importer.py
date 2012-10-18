from __future__ import absolute_import

import os
import re

from PyQt4 import QtCore, QtGui
Qt = QtCore.Qt

from maya import cmds, mel

import ks.core.scene_name.widget as scene_name
from ks.core import product_select


class CameraSelector(product_select.Layout):
    
    def _setup_sections(self):
        super(CameraSelector, self)._setup_sections()
        self.register_section('Camera', self._iter_cameras)
    
    def _iter_cameras(self, step_path):
        if step_path is None:
            return
        camera_dir = os.path.join(step_path, 'maya', 'scenes', 'camera')
        if os.path.exists(camera_dir):
            for name in os.listdir(camera_dir):
                
                if name.startswith('.'):
                    continue
                if not name.endswith('.ma'):
                    continue
                if re.search(r'\.20\d{2}\.ma$', name):
                    continue
                
                m = re.search(r'v(\d+)(?:_r(\d+))?', name)
                if m:
                    priority = tuple(int(x) for x in m.groups())
                else:
                    priority = (0, 0)
                cam_path = os.path.join(camera_dir, name)
                try:
                    ref_node = cmds.referenceQuery(cam_path, referenceNode=True)
                except RuntimeError:
                    pass
                else:
                    name += ' (already referenced)'
                    priority = (-1, 0)
                
                yield name, cam_path, priority


class Dialog(QtGui.QDialog):
    
    def __init__(self):
        super(Dialog, self).__init__()
        self._setup_ui()
    
    def _setup_ui(self):
        
        self.setWindowTitle("Camera Import")
        self.setLayout(QtGui.QVBoxLayout())
        
        self._selector = CameraSelector(parent=self)
        self.layout().addLayout(self._selector)
        
        button = QtGui.QPushButton("Reference")
        button.clicked.connect(self._on_reference)
        self.layout().addWidget(button)
    
    def _on_reference(self, *args):
        path = self._selector.path()
        if path:
            try:
                ref_node = cmds.referenceQuery(path, referenceNode=True)
            except RuntimeError:
                pass
            else:
                cmds.warning('Already referenced')
                return
            cmds.file(path, reference=True)
        self.close()


__also_reload__ = [
    'ks.core.product_select',
]

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
