from __future__ import absolute_import

import os
import re


from uitools.qt import *
from uitools.checkbox import CollapseToggle

from PyQt4 import QtCore, QtGui
Qt = QtCore.Qt

from maya import cmds, mel


class GroupCheckBox(QtGui.QCheckBox):
    
    def __init__(self, group):
        super(GroupCheckBox, self).__init__()
        self._group = group
    
    def nextCheckState(self):
        super(GroupCheckBox, self).nextCheckState()
        state = self.checkState()
        for child in self._group._children:
            child._enabledCheckbox.setChecked(state)


class GroupItem(QtGui.QTreeWidgetItem):

    def __init__(self, name):
        super(GroupItem, self).__init__([name or '<local>'])
        self._name = name
        self._children = []
        self._setupGui()
    
    def _addChild(self, item):
        self._children.append(item)
        self.addChild(item)
    
    def _setupGui(self):
        self._enabledCheckbox = GroupCheckBox(self)

    def _setupTree(self):
        label = QtGui.QLabel('')
        label.setFixedHeight(22)
        self.treeWidget().setItemWidget(self, 0, label)
        self.treeWidget().setItemWidget(self, 1, self._enabledCheckbox)
        self._childUpdated()
    
    def _childUpdated(self):
        new_state = any(x._enabledCheckbox.isChecked() for x in self._children)
        self._enabledCheckbox.setChecked(new_state)
    
    
class SetItem(QtGui.QTreeWidgetItem):
    
    def __init__(self, name, path, namesEnabled):
        super(SetItem, self).__init__([name])

        self._name = name
        self._namesEnabled = namesEnabled

        name_parts = path.split(':')
        name_parts[-1] = name_parts[-1].replace('locators', '_')
        name_parts = [re.sub(r'[\W_]+', '_', x).strip('_') for x in name_parts]
        name_parts[-1] = '_' + name_parts[-1]
        self._export_name = '_'.join(name_parts).strip('_')
        
        self._path = path
        self._setupGui()
    
    def _setupGui(self):

        self._enabledCheckbox = QtGui.QCheckBox(checked=True)
        self._enabledCheckbox.stateChanged.connect(self._onEnabledChanged)

        self._nameField = QtGui.QLineEdit(self._export_name)
        self._nameField.textChanged.connect(self._onNameChanged)

        self._onEnabledChanged()
    
    def _setupTree(self):
        label = QtGui.QLabel('')
        label.setFixedHeight(22)
        self.treeWidget().setItemWidget(self, 0, label)
        self.treeWidget().setItemWidget(self, 1, self._enabledCheckbox)
        self.treeWidget().setItemWidget(self, 2, self._nameField)
    
    def _onEnabledChanged(self, state=None):

        if self._namesEnabled:
            self._nameField.setEnabled(state if state is not None else self._enabledCheckbox.isChecked())
        else:
            self._nameField.setEnabled(False)

        parent = self.parent()
        if parent:
            parent._childUpdated()
    
    def _onNameChanged(self, value):
        self._export_name = str(value)
        

class SetPicker(QtGui.QGroupBox):

    def __init__(self, *args, **kwargs):

        self._pattern = str(kwargs.pop('pattern', '*'))
        self._namesEnabled = bool(kwargs.pop('namesEnabled', False))
        self._gui_is_setup = False

        super(SetPicker, self).__init__(*args, **kwargs)

        self._setupGui()
        self._gui_is_setup = True
    
    def setPattern(self, v):
        self._pattern = str(v)
        if self._gui_is_setup:
            self._pattern_field.setText(self._pattern)

    def setNamesEnabled(self, v):
        self._namesEnabled = bool(v)
        if self._gui_is_setup:
            self._reload()

    def _setupGui(self):

        self.setLayout(QtGui.QVBoxLayout())
        
        tree = self._tree = QtGui.QTreeWidget()
        tree.setFrameShape(QtGui.QFrame.NoFrame)
        tree.setColumnCount(3)
        tree.setHeaderLabels(['Sets in Scene', '', 'Export Name'])
        self.layout().addWidget(tree)
        tree.viewport().setBackgroundRole(QtGui.QPalette.Window)
        tree.setSelectionMode(tree.NoSelection)

        self._option_toggle = CollapseToggle("Options")
        self.layout().addWidget(self._option_toggle)
        self._options_container = QtGui.QFrame(visible=False)
        self.layout().addWidget(self._options_container)
        self._options_container.setContentsMargins(0, 0, 0, 0)
        self._option_toggle.stateChanged.connect(lambda state: self._options_container.setVisible(state))

        self._options_container.setLayout(QtGui.QVBoxLayout())
        self._options_container.layout().setContentsMargins(0, 0, 0, 0)

        pattern_layout = QtGui.QHBoxLayout(spacing=4)
        self._options_container.layout().addLayout(pattern_layout)

        pattern_layout.addWidget(QtGui.QLabel("Include Pattern:"))
        self._pattern_field = field = QtGui.QLineEdit(self._pattern)
        field.returnPressed.connect(self._reload)
        pattern_layout.addWidget(field)

        self._reload_button = button = QtGui.QPushButton('Reload')
        button.clicked.connect(self._reload)
        button.setFixedHeight(field.sizeHint().height())
        button.setFixedWidth(button.sizeHint().width())
        pattern_layout.addWidget(button)
        
        self._reload()
    
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
            child = SetItem(name, set_, self._namesEnabled)
            group._addChild(child)
        
        tree = self._tree
        tree.clear()
        
        if not self._groups:
            item = QtGui.QTreeWidgetItem(["No sets match pattern!"])
            tree.addTopLevelItem(item)
            spacer = QtGui.QLabel('')
            spacer.setFixedHeight(22)
            tree.setItemWidget(item, 0, spacer)

        for reference, group in sorted(self._groups.iteritems(), key=lambda x: (x[0] is not None, x[0])):
            tree.addTopLevelItem(group)
            tree.expandItem(group)
            for child in group._children:
                child._setupTree()
            group._setupTree()
        
        tree.resizeColumnToContents(0)
        tree.setColumnWidth(0, tree.columnWidth(0) + 10)
        tree.setColumnWidth(1, 16)
        tree.resizeColumnToContents(2)
    
    def iterSelectedGroups(self):
        """Return an iterator of (export_name, maya_nodes) pairs."""

        for group in self._groups.itervalues():
            for set_ in group._children:
                
                if not set_._enabledCheckbox.isChecked():
                    continue
        
                members = cmds.sets(set_._path, q=True)
                name = set_._export_name
                
                yield name, members

    def allSelectedNodes(self):
        nodes = set()
        for _, group_nodes in self.iterSelectedGroups():
            nodes.update(group_nodes)
        return list(nodes)



def __before_reload__():
    if dialog:
        dialog.close()

dialog = None

def run(*args, **kwargs):
    
    global dialog
    
    if dialog:
        dialog.close()
    
    dialog = QtGui.QDialog()
    dialog.setLayout(QtGui.QVBoxLayout())
    dialog.layout().addWidget(SetPicker(*args, **kwargs))

    dialog.show()
