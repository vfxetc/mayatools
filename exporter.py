from __future__ import absolute_import

import os
import re

from PyQt4 import QtCore, QtGui
Qt = QtCore.Qt

from maya import cmds, mel

import ks.core.scene_name.widget as scene_name


class Dialog(QtGui.QDialog):
    
    def __init__(self):
        super(Dialog, self).__init__()
        self._setup_ui()
    
    def _setup_ui(self):
        
        self.setWindowTitle("Camera Export")
        self.setLayout(QtGui.QVBoxLayout())
        
        camera_row = QtGui.QHBoxLayout()
        self.layout().addLayout(camera_row)
        
        self._cameras = QtGui.QComboBox()
        camera_row.addWidget(self._cameras)
        self._cameras.activated.connect(self._on_cameras_changed)
        
        button = QtGui.QPushButton("Reload")
        button.clicked.connect(self._on_reload)
        button.setFixedSize(button.sizeHint().boundedTo(QtCore.QSize(1000, 22)))
        camera_row.addWidget(button)
        
        box = QtGui.QGroupBox("Summary")
        self.layout().addWidget(box)
        box.setLayout(QtGui.QVBoxLayout())
        self._summary = QtGui.QLabel("Select a camera.")
        box.layout().addWidget(self._summary)
        
        box = QtGui.QGroupBox("Export Name")
        box.setLayout(QtGui.QVBoxLayout())
        self.layout().addWidget(box)
        self._scene_name = scene_name.SceneNameWidget({
            'scenes_name': 'scenes/camera',
            'sub_directory': '',
            'extension': '.ma',
            'workspace': cmds.workspace(q=True, fullName=True) or None,
            'filename': cmds.file(q=True, sceneName=True) or None,
            'warning': self._warning,
            'error': self._error,
        })
        box.layout().addWidget(self._scene_name)
        
        button_row = QtGui.QHBoxLayout()
        button_row.addStretch()
        self.layout().addLayout(button_row)
        
        button = QtGui.QPushButton("Export")
        button.clicked.connect(self._on_export)
        button_row.addWidget(button)
        
        self._populate_cameras()
    
    def _on_reload(self, *args):
        self._populate_cameras()
    
    def _populate_cameras(self):
        previous = str(self._cameras.currentText())
        selection = set(cmds.ls(sl=True, type='transform') or ())
        self._cameras.clear()
        for camera in cmds.ls(type="camera"):
            transform = cmds.listRelatives(camera, parent=True)[0]
            self._cameras.addItem(transform, (transform, camera))
            if (previous and previous == transform) or (not previous and transform in selection):
                self._cameras.setCurrentIndex(self._cameras.count() - 1)
        self._update_status()
    
    def _on_cameras_changed(self, *args):
        self._update_status()
    
    def _nodes_to_export(self):
        
        transform = str(self._cameras.currentText())
        export = set(cmds.listRelatives(transform, allDescendents=True) or ())
        
        parents = [transform]
        while parents:
            parent = parents.pop(0)
            if parent in export:
                continue
            export.add(parent)
            parents.extend(cmds.listRelatives(parent, allParents=True) or ())
        
        return export
        
    def _update_status(self):
        
        counts = {}
        for node in self._nodes_to_export():
            type_ = cmds.nodeType(node)
            counts[type_] = counts.get(type_, 0) + 1
        
        self._summary.setText('\n'.join('%dx %s' % (c, n) for n, c in sorted(counts.iteritems())))
        
    def _on_export(self, *args):
        
        path = self._scene_name._namer.get_path()
        export_path = path
        print path
        
        dir_name = os.path.dirname(path)
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
            
        # If this is 2013 then export to somewhere temporary.
        maya_version = int(mel.eval('about -version').split()[0])
        if maya_version > 2011:
            export_path = os.path.splitext(path)[0] + ('.%d.ma' % maya_version)
        
        original_selection = cmds.ls(sl=True)
        
        cmds.select(list(self._nodes_to_export()), replace=True)
        cmds.file(export_path, type='mayaAscii', exportSelected=True)
        
        # Rewrite the file to work with 2011.
        if maya_version > 2011:
            
            # Track if the last command was to create an image plane.
            in_image_plane = False
            
            fh = open(path, 'w')
            for line in open(export_path):
                
                # Strip all requires, but add a 2011 requires.
                if line.startswith('requires'):
                    if line.startswith('requires maya'):
                        fh.write('requires maya "2011";\n')
                
                # Strip '-p' off of image planes.
                elif line.startswith('createNode imagePlane'):
                    in_image_plane = True
                    line = re.sub(r'\s*-p "[^"]+"', '', line)
                    fh.write(line)
                
                # Strip this setAttr from image planes.
                elif in_image_plane and line.strip() == 'setAttr -k off ".v";':
                    continue
                
                else:
                    
                    # This is a new command.
                    if line and not line[0].isspace():
                        in_image_plane = False
                    
                    fh.write(line)
            
        if original_selection:
            cmds.select(original_selection, replace=True)
        else:
            cmds.select(clear=True)
        
        self.close()
        
    def _warning(self, message):
        cmds.warning(message)

    def _error(self, message):
        cmds.confirmDialog(title='Scene Name Error', message=message, icon='critical')
        cmds.error(message)


__also_reload__ = ['ks.core.scene_name.widget']
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
