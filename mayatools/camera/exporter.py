from __future__ import absolute_import

import os
import re
import functools

from uitools.qt import QtCore, QtGui, Qt

from maya import cmds, mel

import sgfs.ui.scene_name.widget as scene_name
import sgpublish.exporter.maya
import sgpublish.exporter.ui.publish.maya
import sgpublish.exporter.ui.tabwidget
import sgpublish.exporter.ui.workarea
import sgpublish.uiutils

import mayatools.context
from mayatools import downgrade


# Default Nuke Camera Vert Aperture
DNCVA = 18.672
MODULUS = 25.39999962


class CameraExporter(sgpublish.exporter.maya.Exporter):

    def __init__(self):
        super(CameraExporter, self).__init__(
            workspace=cmds.workspace(q=True, fullName=True) or None,
            filename_hint=cmds.file(q=True, sceneName=True) or 'camera.ma',
            publish_type='maya_camera',
        )
    
    def export_publish(self, publisher, **kwargs):
        
        # Construct a path.
        path = os.path.join(publisher.directory, os.path.basename(self.filename_hint))
        
        # Make sure it is MayaAscii.
        path = os.path.splitext(path)[0] + '.ma'
        
        # Set the primary path (on Shotgun)
        publisher.path = path
        
        return self._export(publisher.directory, path, **kwargs)
        
        
    def export(self, directory, path, **kwargs):
        
        # Make sure it is MayaAscii.
        path = os.path.splitext(path)[0] + '.ma'
        
        return self._export(directory, path, **kwargs)
        
    def _export(self, directory, path, camera, selection=None):
        
        export_path = path
        print '# Exporting camera to %s' % path
        
        if not os.path.exists(directory):
            os.makedirs(directory)
        
        # If this is 2013 then export to somewhere temporary.
        maya_version = int(mel.eval('about -version').split()[0])
        if maya_version > 2011:
            export_path = os.path.splitext(path)[0] + ('.%d.ma' % maya_version)
        
        # Reset camera settings.
        original_zoom = tuple(cmds.getAttr(camera + '.' + attr) for attr in ('horizontalFilmOffset', 'verticalFilmOffset', 'overscan'))
        cmds.setAttr(camera + '.horizontalFilmOffset', 0)
        cmds.setAttr(camera + '.verticalFilmOffset', 0)
        cmds.setAttr(camera + '.overscan', 1)
        
        if selection is not None:
            original_selection = cmds.ls(sl=True)
            cmds.select(selection, replace=True)
        else:
            original_selection = None
        
        # The `constructionHistory` here is only to avoid a bug that crashes
        # Maya 2013. I have no idea why it does that, but it does. It only
        # seems to happen on the second runthrough of this tool, with no
        # changes inbettween (using the mayatools.debug.enable_verbose_commands
        # reveals an identical code path). Hopefully, this fixes it...
        cmds.file(export_path, type='mayaAscii', exportSelected=True, constructionHistory=False)
        
        # Rewrite the file to work with 2011.
        if maya_version > 2011:
            downgrade.downgrade_to_2011(export_path, path)
        
        self._export_nuke(os.path.splitext(path)[0] + '.nk', camera)

        # Restore camera settings.
        cmds.setAttr(camera + '.horizontalFilmOffset', original_zoom[0])
        cmds.setAttr(camera + '.verticalFilmOffset', original_zoom[1])
        cmds.setAttr(camera + '.overscan', original_zoom[2])
        
        # Restore selection.
        if original_selection:
            cmds.select(original_selection, replace=True)
        elif original_selection is not None:
            cmds.select(clear=True)

    def _export_nuke(self, path, camera):

        transform = cmds.listRelatives(camera, fullPath=True, parent=True)[0]

        fh = open(path, 'w')

        fh.write('Camera2 {\n')
        fh.write('\tinputs 0\n')

        name = filter(None, transform.split('|'))[-1]
        name = re.sub(r'\W+', '__', name).strip('_')
        fh.write('\tname "%s"\n' % name)

        fh.write('\trot_order XYZ\n')
        fh.write('\tselected true\n')
        fh.write('\txpos 0\n')
        fh.write('\typos 300\n')

        min_time = int(cmds.playbackOptions(q=True, minTime=True))
        max_time = int(cmds.playbackOptions(q=True, maxTime=True) + 1)

        ts = []
        rs = []
        fs = []
        hfas = []
        vfas = []

        with mayatools.context.suspend_refresh():

            for time in xrange(min_time, max_time):
                cmds.currentTime(time, edit=True)

                ts.append(
                    # We can't just ask for the translation, since it seems to
                    # take the pivot point into account, and there isn't an
                    # obvious (to me) relationship bettween the translate and
                    # pivot info from cmds.xform. Therefor, we extract it from
                    # the full matrix.
                    cmds.xform(transform, q=True, worldSpace=True, matrix=True)[-4:-1]
                )
                rs.append(
                    cmds.xform(transform, q=True, worldSpace=True, rotation=True)
                )
                fs.append(
                    cmds.camera(camera, q=True, focalLength=True)
                )
                hfas.append(
                    cmds.camera(camera, q=True, horizontalFilmAperture=True) * MODULUS
                )
                vfas.append(
                    cmds.camera(camera, q=True, verticalFilmAperture=True) * MODULUS
                )

        fh.write('\ttranslate {\n')
        for i in xrange(3):
            fh.write('\t\t{curve x%d ' % min_time)
            fh.write(' '.join(str(x[i]) for x in ts))
            fh.write('}\n')
        fh.write('\t}\n')

        fh.write('\trotate {\n')
        for i in xrange(3):
            fh.write('\t\t{curve x%d ' % min_time)
            fh.write(' '.join(str(x[i]) for x in rs))
            fh.write('}\n')
        fh.write('\t}\n')

        fh.write('\tfocal {{curve x%d ' % min_time)
        fh.write(' '.join(str(x) for x in fs))
        fh.write('}}\n')

        fh.write('\thaperture {{curve x%d ' % min_time)
        fh.write(' '.join(str(x) for x in hfas))
        fh.write('}}\n')

        fh.write('\tvaperture {{curve x%d ' % min_time)
        fh.write(' '.join(str(x) for x in vfas))
        fh.write('}}\n')

        fh.write('}\n')


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
    
    def _nodes_to_export(self):
        
        transform = str(self._cameras.currentText())
        print 'transform', repr(transform)
        export = set(cmds.listRelatives(transform, allDescendents=True, fullPath=True) or ())
        
        parents = [transform]
        while parents:
            parent = parents.pop(0)
            if parent in export:
                continue
            export.add(parent)
            parents.extend(cmds.listRelatives(parent, allParents=True, fullPath=True) or ())
        
        return export
        
    def _update_status(self):
        
        counts = {}
        for node in self._nodes_to_export():
            type_ = cmds.nodeType(node)
            counts[type_] = counts.get(type_, 0) + 1
        
        self._summary.setText('\n'.join('%dx %s' % (c, n) for n, c in sorted(counts.iteritems())))
        
    def _on_export(self, *args):
        publisher = self._exporter_widget.export(
            camera=self._cameras.itemData(self._cameras.currentIndex()).toPyObject()[1],
            selection=list(self._nodes_to_export()),
        )
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
