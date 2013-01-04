from __future__ import absolute_import

import os
import re

from PyQt4 import QtCore, QtGui
Qt = QtCore.Qt

from maya import cmds, mel

import ks.maya.downgrade

from sgfs.ui import product_select
import sgfs.ui.scene_name.widget as scene_name

import sgpublish.exporter.maya
import sgpublish.exporter.ui.publish.maya
import sgpublish.exporter.ui.tabwidget
import sgpublish.exporter.ui.workarea
import sgpublish.uiutils

from .locators import bake_global_locators
from . import context

class Exporter(sgpublish.exporter.maya.Exporter):

    def __init__(self):
        super(Exporter, self).__init__(
            workspace=cmds.workspace(q=True, fullName=True) or None,
            filename_hint=cmds.file(q=True, sceneName=True) or 'locators',
            publish_type='maya_locators',
        )

    def export_publish(self, publish, **kwargs):
        publish.path = publish.directory
        self.export(publish.directory, publish.path, **kwargs)

    def export(self, _, directory, to_export):

        if not os.path.exists(directory):
            os.makedirs(directory)

        version = int(cmds.about(version=True).split()[0])

        for name, nodes in to_export:

            try:
                locators = bake_global_locators(nodes)
            except ValueError as e:
                cmds.warning(str(e))
                continue

            with context.selection():
                cmds.select(locators, replace=True)

                if version > 2011:
                    path = os.path.join(directory, '%s.%d.ma' % (name, version))
                    path = cmds.file(path, exportSelected=True, type='mayaAscii')
                    ks.maya.downgrade.downgrade_to_2011(
                        path,
                        os.path.join(directory, '%s.ma' % name),
                    )
                else:
                    path = os.path.join(directory, '%s.mb')
                    path = cmds.file(path, exportSelected=True, type='mayaBinary')

            cmds.delete(*locators)






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
        
        name_parts = path.split(':')
        name_parts[-1] = name_parts[-1].replace('locators', '_')
        name_parts = [re.sub(r'[\W_]+', '_', x).strip('_') for x in name_parts]
        name_parts[-1] = '_' + name_parts[-1]
        self._cache_name = '_'.join(name_parts).strip('_')
        
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
        self.setWindowTitle('Locator Export')
        self.setMinimumWidth(600)
        self.setLayout(QtGui.QVBoxLayout())
        
        pattern_layout = QtGui.QHBoxLayout()
        self.layout().addLayout(pattern_layout)
        pattern_layout.addWidget(QtGui.QLabel("Set Pattern:"))
        self._pattern_field = field = QtGui.QLineEdit('__locators__*')
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
        

        self._exporter = Exporter()
        self._exporter_widget = sgpublish.exporter.ui.tabwidget.Widget()
        self.layout().addWidget(self._exporter_widget)

        # Work area.
        tab = sgpublish.exporter.ui.workarea.Widget(self._exporter, {
            'directory': 'data/locators',
            'sub_directory': '',
            'extension': '',
            'workspace': cmds.workspace(q=True, fullName=True) or None,
            'filename': cmds.file(q=True, sceneName=True) or None,
            'warning': self._warning,
            'error': self._warning,
        })
        self._exporter_widget.addTab(tab, "Export to Work Area")
        
        # SGPublishes.
        tab = sgpublish.exporter.ui.publish.maya.Widget(self._exporter)
        tab.beforeScreenshot.connect(lambda *args: self.hide())
        tab.afterScreenshot.connect(lambda *args: self.show())
        self._exporter_widget.addTab(tab, "Publish to Shotgun")

        if 'KS_DEV_ARGS' not in os.environ:
            self._exporter_widget.tabBar().setEnabled(False)
            tab.setEnabled(False)

        button_layout = QtGui.QHBoxLayout()
        self.layout().addLayout(button_layout)
        
        button_layout.addStretch()
        
        button = QtGui.QPushButton("Export")
        button.clicked.connect(self._on_export_button)
        button_layout.addWidget(button)
    
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
    
    def _iter_nodes(self):
        
        for group in self._groups.itervalues():
            for set_ in group._children:
                
                if not set_._enabled_checkbox.isChecked():
                    continue
        
                members = cmds.sets(set_._path, q=True)
                name = set_._cache_name or '__locators__'
                
                yield name, members
        
    def _on_export_button(self):
        publisher = self._exporter_widget.export(to_export=list(self._iter_nodes()))
        if publisher:
            sgpublish.uiutils.announce_publish_success(publisher)
        self.close()


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
