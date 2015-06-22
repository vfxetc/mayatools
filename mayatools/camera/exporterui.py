from __future__ import absolute_import

from uitools.qt import QtCore, QtGui, Qt

from maya import cmds, mel

import sgpublish.exporter.ui.publish.maya
import sgpublish.exporter.ui.tabwidget
import sgpublish.exporter.ui.workarea
import sgpublish.uiutils
from sgpublish.exporter.ui.publish.generic import PublishSafetyError


from .exporter import CameraExporter, get_nodes_to_export




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

        box = QtGui.QGroupBox("Manifest Summary")
        self.layout().addWidget(box)
        box.setLayout(QtGui.QVBoxLayout())
        self._summary = QtGui.QLabel("Select a camera.")
        box.layout().addWidget(self._summary)
        box.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Fixed)
        
        box = QtGui.QGroupBox("Options")
        self.layout().addWidget(box)
        box.setLayout(QtGui.QVBoxLayout())
        self._worldSpaceBox = QtGui.QCheckBox("Bake to World Space (for debugging)")
        box.layout().addWidget(self._worldSpaceBox)

        self._exporter = CameraExporter()
        self._exporter_widget = sgpublish.exporter.ui.tabwidget.Widget()
        self.layout().addWidget(self._exporter_widget)
        
        # SGPublishes.
        tab = sgpublish.exporter.ui.publish.maya.Widget(self._exporter)
        tab.beforeScreenshot.connect(lambda *args: self.hide())
        tab.afterScreenshot.connect(lambda *args: self.show())
        self._exporter_widget.addTab(tab, "Publish to Shotgun")

        # Work area.
        tab = sgpublish.exporter.ui.workarea.Widget(self._exporter, {
            'directory': 'scenes/camera',
            'sub_directory': '',
            'extension': '.ma',
            'warning': self._warning,
            'error': self._warning,
        })
        self._exporter_widget.addTab(tab, "Export to Work Area")
        
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
            transform = cmds.listRelatives(camera, parent=True, fullPath=True)[0]
            self._cameras.addItem(transform, (transform, camera))
            if (previous and previous == transform) or (not previous and transform in selection):
                self._cameras.setCurrentIndex(self._cameras.count() - 1)
        self._update_status()
    
    def _on_cameras_changed(self, *args):
        self._update_status()
            
    def _update_status(self):
        
        transform = str(self._cameras.currentText())
        counts = {}
        for node in get_nodes_to_export(transform):
            type_ = cmds.nodeType(node)
            counts[type_] = counts.get(type_, 0) + 1
        
        self._summary.setText('\n'.join('%dx %s' % (c, n) for n, c in sorted(counts.iteritems())))
        
    def _on_export(self, *args):

        # Other tools don't like cameras named the same as their transform,
        # so this is a good place to warn about it.

        transform, camera = self._cameras.itemData(self._cameras.currentIndex()).toPyObject()
        transform_name = transform.rsplit('|', 1)[-1]
        camera_name = camera.rsplit('|', 1)[-1]
        if transform_name == camera_name:
            res = QtGui.QMessageBox.warning(self, "Camera Name Collision",
                "The selected camera and its transform have the same name, "
                "which can cause issues with other tools.\n\nContinue anyways?",
                "Abort", "Continue")
            if not res:
                return

        try:
            publisher = self._exporter_widget.export(
                camera=camera,
                bake_to_world_space=self._worldSpaceBox.isChecked()
            )
        except PublishSafetyError:
            return

        if publisher:
            sgpublish.uiutils.announce_publish_success(publisher)

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
    
    # Be cautious if the scene was never saved
    filename = cmds.file(query=True, sceneName=True)
    if not filename:
        res = QtGui.QMessageBox.warning(None, 'Unsaved Scene', 'This scene has not beed saved. Continue anyways?',
            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
            QtGui.QMessageBox.No
        )
        if res & QtGui.QMessageBox.No:
            return
    
    workspace = cmds.workspace(q=True, rootDirectory=True)
    if filename and not filename.startswith(workspace):
        res = QtGui.QMessageBox.warning(None, 'Mismatched Workspace', 'This scene is not from the current workspace. Continue anyways?',
            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
            QtGui.QMessageBox.No
        )
        if res & QtGui.QMessageBox.No:
            return
    
    dialog = Dialog()    
    dialog.show()
