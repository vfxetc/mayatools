from __future__ import absolute_import

import os
import re

from PyQt4 import QtCore, QtGui
Qt = QtCore.Qt

from maya import cmds, mel




class CollapseToggle(QtGui.QCheckBox):

    def __init__(self, *args, **kwargs):
        super(CollapseToggle, self).__init__(*args, **kwargs)

    def paintEvent(self, e):

        paint = QtGui.QStylePainter(self)
        option = QtGui.QStyleOptionButton()
        self.initStyleOption(option)

        paint.drawControl(QtGui.QStyle.CE_CheckBox, option)

        # Re-use the style option, it contains enough info to make sure the
        # button is correctly checked
        option.rect = self.style().subElementRect(QtGui.QStyle.SE_CheckBoxIndicator, option, self)

        # Erase the checkbox...
        paint.save();
        px = QtGui.QPixmap(option.rect.width(), option.rect.height())
        px.fill(self, option.rect.left(), option.rect.top())
        brush = QtGui.QBrush(px)
        paint.fillRect(option.rect, brush)
        paint.restore()

        # and replace it with an arrow button
        # option.rect.adjust(3, 0, 0, 0)
        paint.drawPrimitive(QtGui.QStyle.PE_IndicatorArrowDown if self.isChecked() else QtGui.QStyle.PE_IndicatorArrowRight, option)


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
        super(GroupItem, self).__init__([name or '<local>'])
        self._name = name
        self._children = []
        self._setup_ui()
    
    def _add_child(self, item):
        self._children.append(item)
        self.addChild(item)
    
    def _setup_ui(self):
        self._enabled_checkbox = GroupCheckBox(self)

    def _setup_tree(self):
        label = QtGui.QLabel('')
        label.setFixedHeight(22)
        self.treeWidget().setItemWidget(self, 0, label)
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
        self._export_name = '_'.join(name_parts).strip('_')
        
        self._path = path
        self._setup_ui()
    
    def _setup_ui(self):

        self._enabled_checkbox = QtGui.QCheckBox(checked=True)
        self._enabled_checkbox.stateChanged.connect(self._on_enabled_change)

        self._name_field = QtGui.QLineEdit(self._export_name)
        self._name_field.textChanged.connect(self._on_name_change)

        self._on_enabled_change()
    
    def _setup_tree(self):
        label = QtGui.QLabel('')
        label.setFixedHeight(22)
        self.treeWidget().setItemWidget(self, 0, label)
        self.treeWidget().setItemWidget(self, 1, self._enabled_checkbox)
        self.treeWidget().setItemWidget(self, 2, self._name_field)
    
    def _on_enabled_change(self, state=None):
        self._name_field.setEnabled(state if state is not None else self._enabled_checkbox.isChecked())
        parent = self.parent()
        if parent:
            parent._child_updated()
    
    def _on_name_change(self, value):
        self._export_name = str(value)
        

class SetPicker(QtGui.QGroupBox):

    def __init__(self, *args, **kwargs):
        super(SetPicker, self).__init__(*args, **kwargs)
        self._init_ui()
            
    def _init_ui(self):

        self.setLayout(QtGui.QVBoxLayout())
        
        tree = self._sets_tree = QtGui.QTreeWidget()
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
        self._pattern_field = field = QtGui.QLineEdit('__locators__*')
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
            child = SetItem(name, set_)
            group._add_child(child)
        

        tree = self._sets_tree
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
                child._setup_tree()
            group._setup_tree()
        
        tree.resizeColumnToContents(0)
        tree.setColumnWidth(0, tree.columnWidth(0) + 10)
        tree.setColumnWidth(1, 16)
        tree.resizeColumnToContents(2)
    
    def _iter_nodes(self):
        
        for group in self._groups.itervalues():
            for set_ in group._children:
                
                if not set_._enabled_checkbox.isChecked():
                    continue
        
                members = cmds.sets(set_._path, q=True)
                name = set_._export_name or '__locators__'
                
                yield name, members



def __before_reload__():
    if dialog:
        dialog.close()

dialog = None

def run():
    
    global dialog
    
    if dialog:
        dialog.close()
    
    dialog = QtGui.QDialog()
    dialog.setLayout(QtGui.QVBoxLayout())
    dialog.layout().addWidget(SetPicker('Sets to Test'))

    dialog.show()
