from __future__ import absolute_import

import re

from PyQt4 import QtCore, QtGui
Qt = QtCore.Qt

from maya import cmds

from ks.core.scene_name.widget import SceneNameWidget


class Dialog(QtGui.QDialog):

    def __init__(self):
        super(Dialog, self).__init__()
        
        self._init_ui()
    
    def _init_ui(self):
        self.setLayout(QtGui.QVBoxLayout())
        
        tree = self._sets_tree = QtGui.QTreeWidget()
        tree.setColumnCount(3)
        tree.setHeaderLabels(['Geometry', '', 'Export Name'])
        self.layout().addWidget(tree)
        tree.viewport().setBackgroundRole(QtGui.QPalette.Window)
        
        references = {}
        for set_ in cmds.ls(sets=True):
            if ':' in set_:
                reference, name = set_.rsplit(':', 1)
            else:
                reference = '<scene>'
                name = set_
            if 'cache' in name.lower():
                references.setdefault(reference, []).append(name)
        
        for reference, names in sorted(references.iteritems(), key=lambda x: (x[0] != '<scene>', x[0])):
            
            item = QtGui.QTreeWidgetItem([reference, '', ''])
            tree.addTopLevelItem(item)
            
            for name in names:
                child = QtGui.QTreeWidgetItem([name + ' (set)', '', ''])
                item.addChild(child)
                checkbox = QtGui.QCheckBox()
                tree.setItemWidget(child, 1, checkbox)
                
                cache_name = reference + '_' + name
                cache_name = cache_name.replace('cache', '_')
                cache_name = re.sub(r'[\W_]+', '_', cache_name).strip('_')
                edit = QtGui.QLineEdit(cache_name)
                
                edit.setEnabled(False)
                tree.setItemWidget(child, 2, edit)
                checkbox.stateChanged.connect(lambda state, edit=edit: edit.setEnabled(bool(state)))
            
            tree.expandItem(item)
        
        tree.resizeColumnToContents(0)
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
        button.setFixedSize(QtCore.QSize(100, button.sizeHint().height()))
        button_layout.addWidget(button)

        button_layout.addStretch()
        
        button = self._local_button = QtGui.QPushButton("Process Locally")
        button.setFixedSize(QtCore.QSize(100, button.sizeHint().height()))
        button_layout.addWidget(button)
        
        button = self._qube_button = QtGui.QPushButton("Queue on Farm")
        button.setFixedSize(QtCore.QSize(100, button.sizeHint().height()))
        button_layout.addWidget(button)
        
        
        
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
