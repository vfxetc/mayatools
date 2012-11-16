from __future__ import absolute_import

import os
import re

from PyQt4 import QtCore, QtGui
Qt = QtCore.Qt

from maya import cmds, mel

import sgfs.ui.scene_name.widget as scene_name
import sgpublish.ui.exporter
import sgpublish.io.maya

import ks.maya.downgrade as downgrade

__also_reload__ = [
    'ks.maya.downgrade',
    'sgfs.ui.scene_name.widget',
    'sgpublish.ui.exporter',
    'sgpublish.io',
    'sgpublish.io.maya',
]


class CameraExporter(sgpublish.io.maya.Exporter):

    def __init__(self, dialog):
        super(CameraExporter, self).__init__(
            workspace=cmds.workspace(q=True, fullName=True) or None,
            filename_hint=cmds.file(q=True, sceneName=True) or 'camera.ma',
            publish_type='maya_camera',
        )
        self.dialog = dialog
    
    def export(self, directory, path=None):
        
        if path is None:
            path = os.path.join(directory, os.path.basename(self.filename_hint))
        
        export_path = path
        print 'exporting to', path
        
        if not os.path.exists(directory):
            os.makedirs(directory)
            
        # If this is 2013 then export to somewhere temporary.
        maya_version = int(mel.eval('about -version').split()[0])
        if maya_version > 2011:
            export_path = os.path.splitext(path)[0] + ('.%d.ma' % maya_version)
        
        # Reset camera settings.
        camera = self.dialog._cameras.itemData(self.dialog._cameras.currentIndex()).toPyObject()[1]
        original_zoom = tuple(cmds.getAttr(camera + '.' + attr) for attr in ('horizontalFilmOffset', 'verticalFilmOffset', 'overscan'))
        cmds.setAttr(camera + '.horizontalFilmOffset', 0)
        cmds.setAttr(camera + '.verticalFilmOffset', 0)
        cmds.setAttr(camera + '.overscan', 1)
        
        original_selection = cmds.ls(sl=True)
        cmds.select(list(self.dialog._nodes_to_export()), replace=True)
        
        cmds.file(export_path, type='mayaAscii', exportSelected=True)
        
        # Rewrite the file to work with 2011.
        if maya_version > 2011:
            downgrade.downgrade_to_2011(export_path, path)
        
        # Restore camera settings.
        cmds.setAttr(camera + '.horizontalFilmOffset', original_zoom[0])
        cmds.setAttr(camera + '.verticalFilmOffset', original_zoom[1])
        cmds.setAttr(camera + '.overscan', original_zoom[2])
        
        # Restore selection.
        if original_selection:
            cmds.select(original_selection, replace=True)
        else:
            cmds.select(clear=True)
            


class Dialog(QtGui.QDialog):
    
    def __init__(self):
        super(Dialog, self).__init__()
        self._setup_ui()
    
    def _setup_ui(self):
        
        self.setWindowTitle("Camera Export")
        self.setLayout(QtGui.QVBoxLayout())
        self.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Fixed)
        
        camera_row = QtGui.QHBoxLayout()
        camera_row.setSpacing(2)
        self.layout().addLayout(camera_row)
        
        self._cameras = QtGui.QComboBox()
        camera_row.addWidget(self._cameras)
        self._cameras.activated.connect(self._on_cameras_changed)
        
        button = QtGui.QPushButton("Reload")
        button.clicked.connect(self._on_reload)
        button.setFixedHeight(self._cameras.sizeHint().height())
        button.setFixedWidth(button.sizeHint().width())
        camera_row.addWidget(button)
        
        box = QtGui.QGroupBox("Summary")
        self.layout().addWidget(box)
        box.setLayout(QtGui.QVBoxLayout())
        self._summary = QtGui.QLabel("Select a camera.")
        box.layout().addWidget(self._summary)
        box.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Fixed)
        
        self._exporter_widget = sgpublish.ui.exporter.Widget.factory(
            exporter=CameraExporter(self),
            work_area=True,
            publish=True,
            work_area_kwargs={
                'directory': 'scenes/camera',
                'sub_directory': '',
                'extension': '.ma',
                'warning': self._warning,
                'error': self._warning,
            },
        )
        self._exporter_widget.currentChanged.connect(lambda *args: self.adjustSize())
        self._exporter_widget.beforeScreenshot.connect(lambda *args: self.hide())
        self._exporter_widget.afterScreenshot.connect(lambda *args: self.show())
        self.layout().addWidget(self._exporter_widget)
        
        button_row = QtGui.QHBoxLayout()
        button_row.addStretch()
        self.layout().addLayout(button_row)
        
        self._button = button = QtGui.QPushButton("Export")
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
        self._exporter_widget.export()
        self.close()
        
    def _warning(self, message):
        cmds.warning(message)

    def _error(self, message):
        cmds.confirmDialog(title='Scene Name Error', message=message, icon='critical')
        cmds.error(message)


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
