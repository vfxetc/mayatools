from __future__ import absolute_import

import os
import re

from maya import cmds, mel

from sgfs.ui import product_select
from uitools.qt import Qt, QtCore, QtGui
import sgfs.ui.scene_name.widget as scene_name

import sgpublish.exporter.ui.publish.maya
import sgpublish.exporter.ui.tabwidget
import sgpublish.exporter.ui.workarea
import sgpublish.uiutils
from sgpublish.exporter.ui.publish.generic import PublishSafetyError

from .exporter import Exporter, cache_name_from_cache_set


class GroupCheckBox(QtGui.QCheckBox):
    
    def __init__(self, group):
        super(GroupCheckBox, self).__init__()
        self._group = group
    
    def nextCheckState(self):
        super(GroupCheckBox, self).nextCheckState()
        state = self.checkState()
        for child in self._group._children:
            child._enabled_checkbox.setChecked(state)


class GroupItem(QtGui.QTreeWidgetItem):

    def __init__(self, name):
        super(GroupItem, self).__init__([name or '<scene>'])
        self._name = name
        self._children = []
        self._setup_ui()
    
    def _add_child(self, item):
        self._children.append(item)
        self.addChild(item)
    
    def _setup_ui(self):
        self._enabled_checkbox = GroupCheckBox(self)

    def _setup_tree(self):
        self.treeWidget().setItemWidget(self, 1, self._enabled_checkbox)
        self._child_updated()
    
    def _child_updated(self):
        new_state = any(x._enabled_checkbox.isChecked() for x in self._children)
        self._enabled_checkbox.setChecked(new_state)
    
    
class SetItem(QtGui.QTreeWidgetItem):
    
    def __init__(self, name, path):
        super(SetItem, self).__init__([name])
        self._name = name
        self._cache_name = cache_name_from_cache_set(path)
        
        self._path = path
        self._setup_ui()
    
    def _setup_ui(self):
        self._enabled_checkbox = QtGui.QCheckBox()
        self._enabled_checkbox.setChecked(True)
        self._enabled_checkbox.stateChanged.connect(self._on_enabled_change)
        self._cache_name_field = QtGui.QLineEdit(self._cache_name)
        self._cache_name_field.textChanged.connect(self._on_name_change)
        self._on_enabled_change()
    
    def _setup_tree(self):
        self.treeWidget().setItemWidget(self, 1, self._enabled_checkbox)
        self.treeWidget().setItemWidget(self, 2, self._cache_name_field)
    
    def _on_enabled_change(self, state=None):
        self._cache_name_field.setEnabled(state if state is not None else self._enabled_checkbox.isChecked())
        parent = self.parent()
        if parent:
            parent._child_updated()
    
    def _on_name_change(self, value):
        self._cache_name = str(value)
        
                

class Dialog(QtGui.QDialog):

    def __init__(self):
        super(Dialog, self).__init__()
        
        self._init_ui()
    
    def _warning(self, message):
        cmds.warning(message)

    def _error(self, message):
        cmds.confirmDialog(title='Scene Name Error', message=message, icon='critical')
        cmds.error(message)
            
    def _init_ui(self):
        self.setWindowTitle('Alembic Cache Export')
        self.setMinimumWidth(600)
        self.setLayout(QtGui.QVBoxLayout())
        
        pattern_layout = QtGui.QHBoxLayout()
        self.layout().addLayout(pattern_layout)
        pattern_layout.addWidget(QtGui.QLabel("Set Pattern:"))
        self._pattern_field = field = QtGui.QLineEdit('__geoCache__')
        field.returnPressed.connect(self._reload)
        pattern_layout.addWidget(field)
        self._reload_button = button = QtGui.QPushButton('Reload')
        button.clicked.connect(self._reload)
        pattern_layout.addWidget(button)
        
        tree = self._sets_tree = QtGui.QTreeWidget()
        tree.setFrameShadow(QtGui.QFrame.Plain)
        tree.setColumnCount(3)
        tree.setHeaderLabels(['Geometry', '', 'Export Name'])
        self.layout().addWidget(tree)
        tree.viewport().setBackgroundRole(QtGui.QPalette.Window)
        
        self._reload()
        
        '''
        options_box = QtGui.QGroupBox('Options')
        self.layout().addWidget(options_box)
        options_box.setLayout(QtGui.QVBoxLayout())
        '''
        version = int(cmds.about(version=True).split()[0])
        layout = QtGui.QHBoxLayout()
        #options_box.layout().addLayout(layout)
        label = QtGui.QLabel("Store Points In:")
        label.setEnabled(version >= 2013)
        layout.addWidget(label)
        group = QtGui.QButtonGroup()
        self._local_radio = QtGui.QRadioButton('Local Space')
        self._local_radio.setEnabled(version >= 2013)
        group.addButton(self._local_radio)
        layout.addWidget(self._local_radio)
        self._world_radio = QtGui.QRadioButton('World Space')
        self._world_radio.setEnabled(version >= 2013)
        group.addButton(self._world_radio)
        layout.addWidget(self._world_radio)
        layout.addStretch()

        if version < 2013:
            label = QtGui.QLabel('(only in 2013+)')
            label.setEnabled(False)
            layout.addWidget(label)
            self._local_radio.setChecked(True)
        else:
            self._world_radio.setChecked(True)
        
        self._abc_check = QtGui.QCheckBox("Also export as Alembic")
        #options_box.layout().addWidget(self._abc_check)
        if hasattr(cmds, 'AbcExport'):
            self._abc_check.setChecked(True)
        else:
            self._abc_check.setDisabled(True)
        
        self._abc_check.setChecked(True)
        self._exporter = Exporter()
        self._exporter_widget = sgpublish.exporter.ui.tabwidget.Widget()
        self.layout().addWidget(self._exporter_widget)
        
        # SGPublishes.
        tab = sgpublish.exporter.ui.publish.maya.Widget(self._exporter)
        tab.beforeScreenshot.connect(lambda *args: self.hide())
        tab.afterScreenshot.connect(lambda *args: self.show())
        self._exporter_widget.addTab(tab, "Publish to Shotgun")

        # Work area.
        tab = sgpublish.exporter.ui.workarea.Widget(self._exporter, {
            'directory': 'data/geo_cache',
            'sub_directory': '',
            'extension': '',
            'workspace': cmds.workspace(q=True, fullName=True) or None,
            'filename': cmds.file(q=True, sceneName=True) or None,
            'warning': self._warning,
            'error': self._warning,
        })
        self._exporter_widget.addTab(tab, "Export to Work Area")
        
        button_layout = QtGui.QHBoxLayout()
        self.layout().addLayout(button_layout)
        
        button = self.cancel_button = QtGui.QPushButton("Cancel")
        button.clicked.connect(self._on_cancel_button)
        button_layout.addWidget(button)
        button_layout.addStretch()
        
        button = self._local_button = QtGui.QPushButton("Process Locally")
        button.clicked.connect(self._on_process_button)
        button_layout.addWidget(button)
        '''
        button = self._qube_button = QtGui.QPushButton("Process on Farm")
        button.clicked.connect(self._on_queue_button)
        button_layout.addWidget(button)
        '''

    def _reload(self):
        
        self._groups = {}
        
        pattern = str(self._pattern_field.text())
        patterns = [x.strip() for x in pattern.split(',')]
        for set_ in sorted(set(cmds.ls(*patterns, sets=True, recursive=True, long=True))):
            
            if ':' in set_:
                reference, name = set_.rsplit(':', 1)
            else:
                reference = None
                name = set_
            
            group = self._groups.get(reference)
            if group is None:
                group = GroupItem(reference)
                self._groups[reference] = group
            child = SetItem(name, set_)
            group._add_child(child)
        
        tree = self._sets_tree
        tree.clear()
        
        for reference, group in sorted(self._groups.iteritems(), key=lambda x: (x[0] is not None, x[0])):
            tree.addTopLevelItem(group)
            tree.expandItem(group)
            for child in group._children:
                child._setup_tree()
            group._setup_tree()
        
        tree.resizeColumnToContents(0)
        tree.setColumnWidth(0, tree.columnWidth(0) + 10)
        tree.setColumnWidth(1, 16)
    
    def _on_save_button(self):
        cmds.error('Not Implemented')
    
    def _iter_to_cache(self):
        
        frame_from = cmds.playbackOptions(q=True, animationStartTime=True)
        frame_to = cmds.playbackOptions(q=True, animationEndTime=True)
        world = self._world_radio.isChecked()
        
        for group in self._groups.itervalues():
            for set_ in group._children:
                
                if not set_._enabled_checkbox.isChecked():
                    continue
        
                members = cmds.sets(set_._path, q=True)
                name = set_._cache_name or '__cache__'
                
                yield members, name, frame_from, frame_to, world
        
    def _on_process_button(self, on_farm=False):
        
        to_cache = list(self._iter_to_cache())
        if not to_cache:
            QtGui.QMessageBox.critical(self, "Error", "Nothing selected to export.")
            return

        try:
            publisher = self._exporter_widget.export(
                to_cache=to_cache,
                as_abc=self._abc_check.isChecked(),
                on_farm=on_farm,
            )
        except PublishSafetyError:
            return

        if publisher:
            sgpublish.uiutils.announce_publish_success(publisher)
        self.close()
        
    def _on_queue_button(self):
        self._on_process_button(on_farm=True)

    def _on_cancel_button(self):
        self.close()


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
