from __future__ import absolute_import

import contextlib
import os
import re
import functools

from maya import cmds

from uitools.qt import QtCore, QtGui, Qt
from uitools.layout import vbox, hbox

from .retime import schedule_retime


def selected_fluid_caches():
    return find_related_fluid_caches(cmds.ls(sl=True) or ())


def find_related_fluid_caches(nodes):

    nodes = list(nodes)

    visited = set()
    cache_map = dict()
    while nodes:
        
        node = nodes.pop(0)
        if node in visited:
            continue
        visited.add(node)
        
        type_ = cmds.nodeType(node)
        
        if type_ == 'transform':
            nodes.extend(cmds.listRelatives(node, path=True, children=True) or ())
            continue
        
        if type_ == 'fluidShape':
            caches = list(set(cmds.listConnections(node, type='cacheFile') or ()))
            if caches:
                cache_map[node] = caches[0]
            continue
        
    return cache_map


class RetimeUI(object):

    def __init__(self, widget):

        widget.setMinimumWidth(600)
        self.layout = QtGui.QVBoxLayout()
        widget.setLayout(self.layout)

        src = QtGui.QGroupBox('Source')
        src.setLayout(vbox())
        self.layout.addWidget(src)

        directory = cmds.getAttr(widget._cacheNode + '.cachePath')
        directory = os.path.normpath(directory)
        self.srcDirectory = QtGui.QLineEdit(directory)
        self.srcDirectoryBrowse = QtGui.QPushButton("Browse")
        src.layout().addLayout(hbox("Directory", self.srcDirectory, self.srcDirectoryBrowse))

        base_name = cmds.getAttr(widget._cacheNode + '.cacheName')
        self.srcName = QtGui.QLineEdit(base_name)
        layout = hbox("Cache Name", self.srcName)
        layout.addStretch()
        src.layout().addLayout(layout)

        self.srcStart = QtGui.QDoubleSpinBox(value=cmds.getAttr(widget._cacheNode + '.sourceStart'), maximum=100000)
        self.srcEnd = QtGui.QDoubleSpinBox(value=cmds.getAttr(widget._cacheNode + '.sourceEnd'), maximum=100000)
        layout = hbox("From", self.srcStart, 'to', self.srcEnd)
        layout.addStretch()
        src.layout().addLayout(layout)

        dst = QtGui.QGroupBox("Destination")
        dst.setLayout(vbox())
        self.layout.addWidget(dst)

        self.dstDirectory = QtGui.QLineEdit(directory)
        self.dstDirectoryBrowse = QtGui.QPushButton("Browse")
        dst.layout().addLayout(hbox("Directory", self.dstDirectory, self.dstDirectoryBrowse))

        self.dstName = QtGui.QLineEdit(base_name)
        layout = hbox("Cache Name", self.dstName)
        layout.addStretch()
        dst.layout().addLayout(layout)

        self.dstStart = QtGui.QDoubleSpinBox(value=cmds.getAttr(widget._cacheNode + '.sourceStart'), maximum=100000)
        self.dstEnd = QtGui.QDoubleSpinBox(value=cmds.getAttr(widget._cacheNode + '.sourceEnd'), maximum=100000)
        layout = hbox("From", self.dstStart, 'to', self.dstEnd)
        layout.addStretch()
        dst.layout().addLayout(layout)

        opts = QtGui.QGroupBox('Options')
        opts.setLayout(vbox())
        self.layout.addWidget(opts)

        self.samplingRate = QtGui.QDoubleSpinBox(value=1)
        layout = hbox('Sampling Rate', self.samplingRate)
        layout.addStretch()
        opts.layout().addLayout(layout)

        self.workers = QtGui.QSpinBox(value=20)
        layout = hbox('Farm Workers', self.workers)
        layout.addStretch()
        opts.layout().addLayout(layout)

        self.buttonRow = QtGui.QHBoxLayout()
        self.buttonRow.addStretch()
        self.layout.addLayout(self.buttonRow)

        self.exportButton = QtGui.QPushButton("Submit to Qube")
        self.buttonRow.addWidget(self.exportButton)


class Dialog(QtGui.QDialog):
    
    UI = RetimeUI

    def __init__(self, transformNode, cacheNode):
        super(Dialog, self).__init__()

        self._transformNode = transformNode
        self._cacheNode = cacheNode

        self._setup_ui()
    
    def _setup_ui(self):
        
        self.setWindowTitle("Retime Fluid")
        self.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Fixed)
        
        self.ui = self.UI(self)
        self.ui.exportButton.clicked.connect(self._on_exportButton_clicked)
        self.ui.srcDirectoryBrowse.clicked.connect(functools.partial(self._on_browse_clicked, self.ui.srcDirectory))
        self.ui.dstDirectoryBrowse.clicked.connect(functools.partial(self._on_browse_clicked, self.ui.dstDirectory))
        
    def _on_browse_clicked(self, dstWidget):
        startingDirectory = os.path.dirname(str(dstWidget.text()))
        if not os.path.exists(startingDirectory):
            startingDirectory = cmds.workspace(query=True, rootDirectory=True)
        directory = cmds.fileDialog2(dialogStyle=2, startingDirectory=startingDirectory, fileMode=3)
        if directory:
            dstWidget.setText(directory[0])

    def _on_exportButton_clicked(self, *args):

        src_path = os.path.join(
            str(self.ui.srcDirectory.text()),
            str(self.ui.srcName.text()) + '.xml'
        )
        dst_path = os.path.join(
            str(self.ui.dstDirectory.text()),
            str(self.ui.dstName.text()) + '.xml'
        )

        if src_path == dst_path:
            QtGui.QMessageBox.critical(None,
                'Source is Destination',
                'Source and destination must be different!',
                QtGui.QMessageBox.Abort,
            )
            return

        if not os.path.exists(src_path):
            QtGui.QMessageBox.critical(None,
                'Source Missing',
                'The specified source XML does not exist.',
                QtGui.QMessageBox.Abort,
            )
            return

        src_start = self.ui.srcStart.value()
        src_end = self.ui.srcEnd.value()
        dst_start = self.ui.dstStart.value()
        dst_end = self.ui.dstEnd.value()
        sampling_rate = self.ui.samplingRate.value()
        if src_start == dst_start and src_end == dst_end and sampling_rate == 1.0:
            QtGui.QMessageBox.critical(None,
                'No Change',
                'There is no change in timing requested.',
                QtGui.QMessageBox.Abort,
            )
            return

        if os.path.exists(dst_path):
            res = QtGui.QMessageBox.warning(None,
                'Destination Exists',
                'The destination already exists; do you want to continue and replace it?',
                QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel,
            )
            if res & QtGui.QMessageBox.Cancel:
                return

        job_id = schedule_retime(
            src_path=src_path,
            dst_path=dst_path,
            src_start=self.ui.srcStart.value(),
            src_end=self.ui.srcEnd.value(),
            dst_start=self.ui.dstStart.value(),
            dst_end=self.ui.dstEnd.value(),
            sampling_rate=self.ui.samplingRate.value(),
            farm=True,
            workers=self.ui.workers.value(),
        )
        print 'Qube Job ID:', job_id

        QtGui.QMessageBox.information(None,
            'Submitted to Qube',
            'Submitted to Qube as Job %d' % job_id,
        )

        self.close()



def __before_reload__():
    if dialog:
        dialog.close()

dialog = None

def run():
    
    global dialog
    
    if dialog:
        dialog.close()
    
    cache_map = selected_fluid_caches()
    if not cache_map:
        QtGui.QMessageBox.critical(None, 'No Cached Fluid', 'Please select a fluid with a cache.',
            QtGui.QMessageBox.Abort,
        )
        return
    if len(cache_map) != 1:
        QtGui.QMessageBox.critical(None, 'Too Many Selections', 'Please select a single fluid with a cache.',
            QtGui.QMessageBox.Abort,
        )
        return

    dialog = Dialog(*cache_map.items()[0])    
    dialog.show()
