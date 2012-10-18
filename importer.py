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
                if not name.startswith('.') and name.endswith('.ma'):
                    yield name, os.path.join(camera_dir, name), 0
    
    def path_changed(self, path):
        print 'NEW PATH', repr(path)


class Dialog(QtGui.QDialog):
    
    def __init__(self):
        super(Dialog, self).__init__()
        self._setup_ui()
    
    def _setup_ui(self):
        
        self.setWindowTitle("Camera Import")
        self.setLayout(QtGui.QVBoxLayout())
        
        self._selector = CameraSelector(parent=self)
        self.layout().addLayout(self._selector)


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
