from __future__ import absolute_import

import re

from PyQt4 import QtCore, QtGui
Qt = QtCore.Qt

from maya import cmds

from ks.core.scene_name.widget import SceneNameWidget


class GroupItem(QtGui.QTreeWidgetItem):

    def __init__(self, name):
        super(GroupItem, self).__init__([name or '<scene>'])
        self._name = name
        self._children = []
    
    def _add_child(self, item):
        self._children.append(item)
        self.addChild(item)
        
    
class SetItem(QtGui.QTreeWidgetItem):
    
    def __init__(self, name, path):
        super(SetItem, self).__init__([name])
        self._name = name
        
        name_parts = path.split(':')
        name_parts[-1] = name_parts[-1].replace('cache', '_')
        name_parts = [re.sub(r'[\W_]+', '_', x).strip('_') for x in name_parts]
        name_parts[-1] = '_' + name_parts[-1]
        self._cache_name = '_'.join(name_parts).strip('_')
        
        self._path = path
        self._setup_ui()
    
    def _setup_ui(self):
        self._enabled_checkbox = QtGui.QCheckBox()
        self._enabled_checkbox.stateChanged.connect(self._on_enabled_change)
        self._cache_name_field = QtGui.QLineEdit(self._cache_name)
        self._on_enabled_change()
    
    def _setup_tree(self):
        self.treeWidget().setItemWidget(self, 1, self._enabled_checkbox)
        self.treeWidget().setItemWidget(self, 2, self._cache_name_field)
    
    def _on_enabled_change(self, state=False):
        self._cache_name_field.setEnabled(state)
        
                

class Dialog(QtGui.QDialog):

    def __init__(self):
        super(Dialog, self).__init__()
        
        self._init_ui()
    
    def _init_ui(self):
        self.setMinimumWidth(600)
        self.setLayout(QtGui.QVBoxLayout())
        
        tree = self._sets_tree = QtGui.QTreeWidget()
        # tree.setFrameShape(QtGui.QFrame.NoFrame)
        tree.setFrameShadow(QtGui.QFrame.Plain)
        tree.setColumnCount(3)
        tree.setHeaderLabels(['Geometry', '', 'Export Name'])
        self.layout().addWidget(tree)
        tree.viewport().setBackgroundRole(QtGui.QPalette.Window)
        
        groups = {}
        for set_ in cmds.ls(sets=True):
            
            if ':' in set_:
                reference, name = set_.rsplit(':', 1)
            else:
                reference = None
                name = set_
            
            if 'cache' in name.lower():
                group = groups.get(reference)
                if group is None:
                    group = GroupItem(reference)
                    groups[reference] = group
                child = SetItem(name, set_)
                group._add_child(child)
        
        for reference, group in sorted(groups.iteritems(), key=lambda x: (x[0] is not None, x[0])):
            tree.addTopLevelItem(group)
            tree.expandItem(group)
            for child in group._children:
                child._setup_tree()
        
        tree.resizeColumnToContents(0)
        tree.setColumnWidth(0, tree.columnWidth(0) + 10)
        tree.setColumnWidth(1, 16)
        
        box = self._scene_name_box = QtGui.QGroupBox()
        box.setLayout(QtGui.QVBoxLayout())
        self.layout().addWidget(box)
    
        self._scene_name = SceneNameWidget(dict(
            scenes_name='data/geoCache',
            sub_directory='',
            workspace=cmds.workspace(q=True, rd=True),
        ))
        box.layout().addWidget(self._scene_name)
    
        button_layout = QtGui.QHBoxLayout()
        self.layout().addLayout(button_layout)
    
        button = self._save_button = QtGui.QPushButton("Save Settings")
        button.clicked.connect(self._on_save_button)
        button.setFixedSize(QtCore.QSize(100, button.sizeHint().height()))
        button_layout.addWidget(button)

        button_layout.addStretch()
        
        button = self._local_button = QtGui.QPushButton("Process Locally")
        button.clicked.connect(self._on_process_button)
        button.setFixedSize(QtCore.QSize(100, button.sizeHint().height()))
        button_layout.addWidget(button)
        
        button = self._qube_button = QtGui.QPushButton("Queue on Farm")
        button.clicked.connect(self._on_queue_button)
        button.setFixedSize(QtCore.QSize(100, button.sizeHint().height()))
        button_layout.addWidget(button)
        
    def _on_save_button(self):
        cmds.error('Not Implemented')
        
    def _on_process_button(self):
        cmds.error('Not Implemented')
        
    def _on_queue_button(self):
        cmds.error('Not Implemented')
        
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
