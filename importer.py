from __future__ import absolute_import

import os
import re

from PyQt4 import QtCore, QtGui
Qt = QtCore.Qt

from maya import cmds, mel

from ks.core.scene_name.core import SceneName


class Link(QtGui.QGroupBox):
    
    def __init__(self, index):
        super(Link, self).__init__("Link %d" % index)
        self._setup_ui()
    
    def _setup_ui(self):
        
        # Lots of layouts...
        self.setLayout(QtGui.QHBoxLayout())
        self._main_layout = QtGui.QVBoxLayout()
        self.layout().addLayout(self._main_layout)
        self._cache_layout = QtGui.QHBoxLayout()
        self._main_layout.addLayout(self._cache_layout)
        self._reference_layout = QtGui.QHBoxLayout()
        self._main_layout.addLayout(self._reference_layout)
        
        # Cache widgets
        
        self._shot_combo = QtGui.QComboBox()
        self._populate_shot_combo()        
        self._shot_combo.currentIndexChanged.connect(self._on_shot_changed)
        self._cache_layout.addWidget(self._shot_combo)

        self._step_combo = QtGui.QComboBox()
        self._step_combo.currentIndexChanged.connect(self._on_step_changed)
        self._cache_layout.addWidget(self._step_combo)
        
        self._cache_combo = QtGui.QComboBox()
        self._cache_combo.currentIndexChanged.connect(self._on_cache_changed)
        self._cache_layout.addWidget(self._cache_combo)
        
        self._name_combo = QtGui.QComboBox()
        self._name_combo.currentIndexChanged.connect(self._on_name_changed)
        self._cache_layout.addWidget(self._name_combo)
        
        self._cache_field = QtGui.QLineEdit()
        self._cache_browse_button = QtGui.QPushButton("Browse")
        self._cache_browse_button.setMaximumSize(QtCore.QSize(50, 20))
        self._cache_browse_button.clicked.connect(self._on_cache_browse)
        self._cache_layout.addWidget(self._cache_field)
        self._cache_layout.addWidget(self._cache_browse_button)
        
        
        self._on_shot_changed()
        
        # Cache widgets
        self._reference_combo = QtGui.QComboBox()
        # self._reference_combo.addItem("Reindeer")
        self._reference_combo.addItem("Custom")
        self._reference_combo.currentIndexChanged.connect(self._on_reference_changed)
        self._reference_layout.addWidget(self._reference_combo)
        self._selection_field = QtGui.QLineEdit()
        self._set_selection_button = QtGui.QPushButton("Set to Selection")
        self._set_selection_button.setMaximumSize(
            self._set_selection_button.sizeHint().boundedTo(QtCore.QSize(1000, 20))
        )
        self._set_selection_button.clicked.connect(self._on_set_clicked)
        self._reference_layout.addWidget(self._selection_field)
        self._reference_layout.addWidget(self._set_selection_button)
        self._on_reference_changed()
        
        # Delete button.
        self._delete_button = QtGui.QPushButton('Unlink')
        self._delete_button.setMaximumSize(QtCore.QSize(50, 20))
        self._delete_button.clicked.connect(self._on_delete_clicked)
        self.layout().addWidget(self._delete_button)
    
    def _populate_shot_combo(self):
        
        self._shot_combo.clear()
        
        # Populate shot combo with all reuses that match the current workspace.
        workspace = cmds.workspace(q=True, directory=True)
        m = re.match(r'(.+?)/SEQ/(\w{2})/(\w+)(?:/|$)', workspace)
        if m:
            root, seq, self._current_shot = m.groups()
            m = re.match(r'%s_(\d{3})_(\d{3})$' % seq, self._current_shot)
            if m:
                use, reuse = m.groups()
                for file_name in os.listdir(os.path.join(root, 'SEQ', seq)):
                    if re.match(r'%s_%s_\d{3}$' % (seq, use), file_name):
                        self._shot_combo.addItem(file_name)
                        if file_name == self._current_shot:
                            self._shot_combo.setCurrentIndex(self._shot_combo.count() - 1)
        
        self._shot_combo.addItem('Custom')
    
    def _populate_step_combo(self):
        self._step_combo.clear()
        namer = SceneName(
            workspace=cmds.workspace(q=True, directory=True).replace(self._current_shot, str(self._shot_combo.currentText())),
            warning=cmds.warning,
            error=cmds.warning,
        )
        steps = namer.get_step_names()
        if not steps:
            return
        for i, name in enumerate(steps):
            self._step_combo.addItem(name)
            if name.lower().startswith('anim'):
                self._step_combo.setCurrentIndex(i)
        
    def _on_shot_changed(self, index=None):
        shot = str(self._shot_combo.currentText())
        
        is_custom = shot == 'Custom'
        self._cache_field.setVisible(is_custom)
        self._cache_browse_button.setVisible(is_custom)
        self._step_combo.setVisible(not is_custom)
        self._cache_combo.setVisible(not is_custom)
        self._name_combo.setVisible(not is_custom)
        
        if not is_custom:
            self._populate_step_combo()
            self._on_step_changed()
    
    def _on_step_changed(self, index=None):
        shot = str(self._step_combo.currentText())
        self._populate_cache_combo()
        
    def _populate_cache_combo(self):
        self._cache_combo.clear()
        self._cache_combo.addItem('Select...')
        # TODO: Do this with SGFS.
        path = cmds.workspace(q=True, directory=True)
        path = path[:path.find(self._current_shot)] + str(self._shot_combo.currentText())
        path = os.path.join(path, str(self._step_combo.currentText()), 'maya', 'data', 'geo_cache')
        if os.path.exists(path):
            for name in os.listdir(path):
                self._cache_combo.addItem(name)
    
    def _on_cache_changed(self, index=None):
        pass
    
    def _populate_name_combo(self):
        pass
    
    def _on_name_changed(self, index=None):
        pass
    
    def _populate_reference_combo(self):
        pass
    
    def _on_reference_changed(self, index=None):
        reference = str(self._reference_combo.currentText())
        
        is_custom = reference == 'Custom'
        self._selection_field.setVisible(is_custom)
        self._set_selection_button.setVisible(is_custom)
        
    def _on_cache_browse(self):
        file_name = str(QtGui.QFileDialog.getOpenFileName(self, "Select Geocache", os.getcwd(), "Geocaches (*.xml)"))
        if not file_name:
            return

        workspace = cmds.workspace(q=True, directory=True)
        relative = os.path.relpath(file_name, workspace)
        if relative.startswith('.'):
            self._cache_field.setText(file_name)
        else:
            self._cache_field.setText(relative)
    
    def _on_set_clicked(self):
        self._selection_field.setText(', '.join(cmds.ls(selection=True)))
        
    def _on_delete_clicked(self):
        self.destroy()
        

class Dialog(QtGui.QMainWindow):

    def __init__(self):
        super(Dialog, self).__init__()
        
        self._init_ui()
    
    def _init_ui(self):
        self.setWindowTitle('Geocache Import')
        self.setMinimumWidth(700)
        
        self._scroll_widget = area = QtGui.QScrollArea()
        area.setFrameShape(QtGui.QFrame.NoFrame)
        area.setWidgetResizable(True)
        self.setCentralWidget(area)
        area_widget = QtGui.QWidget()
        self._scroll_layout = layout = QtGui.QVBoxLayout()
        area_widget.setLayout(layout)
        area.setWidget(area_widget)
        
        self._add_button = button = QtGui.QPushButton("Add Link...")
        layout.addWidget(button)
        button.clicked.connect(self._on_add_link)
        
        layout.addStretch()
        
        self._on_add_link()
    
    def _on_add_link(self):
        link = Link(self._scroll_layout.count() - 1)
        self._scroll_layout.insertWidget(self._scroll_layout.count() - 2, link)

__also_reload__ = ['ks.core.scene_name.core']
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
        