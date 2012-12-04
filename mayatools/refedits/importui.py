import os
import re
import collections

from PyQt4 import QtCore, QtGui
Qt = QtCore.Qt

from maya import cmds, mel

from sgfs.ui import product_select
import sgfs.ui.scene_name.widget as scene_name

__also_reload__ = [
    'sgfs.ui.scene_name.widget',
    'sgfs.ui.product_select',
]


RefEdit = collections.namedtuple('RefEdit', ('command', 'namespaces', 'source'))


class RefEditSelector(product_select.Layout):
    
    def _setup_sections(self):
        super(RefEditSelector, self)._setup_sections()
        self.register_section('Ref Edits', self._iter_files)
    
    def _iter_files(self, step_path):
        if step_path is None:
            return
            
        refedit_dir = os.path.join(step_path, 'maya', 'data', 'refedits')
        if not os.path.exists(refedit_dir):
            return
        
        for name in os.listdir(refedit_dir):
                
            if name.startswith('.'):
                continue
            if not name.endswith('.mel'):
                continue
                
            m = re.search(r'v(\d+)(?:_r(\d+))?', name)
            if m:
                priority = tuple(int(x or 0) for x in m.groups())
            else:
                priority = (0, 0)
            
            refedit_path = os.path.join(refedit_dir, name)
            yield name, refedit_path, priority


class Dialog(QtGui.QDialog):
    
    def __init__(self):
        super(Dialog, self).__init__()
        self._setup_ui()
    
    def _setup_ui(self):
        
        self.setWindowTitle("Reference Edit Import")
        self.setLayout(QtGui.QVBoxLayout())
        
        self._selector = RefEditSelector(parent=self)
        
        # Select as far as we can.
        path = (
            cmds.file(q=True, sceneName=True) or
            cmds.workspace(q=True, fullName=True) or
            None
        )
        if path is not None:
            self._selector.setPath(path, allow_partial=True)
        
        self.layout().addLayout(self._selector)
        
        self._type_box = QtGui.QGroupBox("Edit Types")
        self._type_box.setLayout(QtGui.QVBoxLayout())
        self.layout().addWidget(self._type_box)
        
        self._namespace_box = QtGui.QGroupBox("Namespace Mappings")
        self._namespace_box.setLayout(QtGui.QVBoxLayout())
        self.layout().addWidget(self._namespace_box)
        
        button = QtGui.QPushButton("Apply Edits")
        button.clicked.connect(self._on_reference)
        self.layout().addWidget(button)

        self._selector.path_changed = self._path_changed
        self._path_changed(self._selector.path())
    
    def _parse_file(self, path):
        
        self._edits = []
        for line in open(path):
            line = line.strip()
            if not line or line.startswith('//'):
                continue
            command = line.split()[0]
            namespaces = re.findall(r'(\w+):', line)
            self._edits.append(RefEdit(
                command=command,
                namespaces=set(namespaces),
                source=line,
            ))
            
        
    def _path_changed(self, path):
        
        for child in self._type_box.children():
            if isinstance(child, QtGui.QWidget):
                child.hide()
                child.destroy()
        for child in self._namespace_box.children():
            if isinstance(child, QtGui.QWidget):
                child.hide()
                child.destroy()
            
        if path is None:
            self._type_box.layout().addWidget(QtGui.QLabel("Nothing"))
            self._namespace_box.layout().addWidget(QtGui.QLabel("Nothing"))
            return
        
        self._parse_file(path)
        
        self._command_boxes = []
        for command in sorted(set(e.command for e in self._edits)):
            checkbox = QtGui.QCheckBox(command)
            checkbox.setChecked(command == 'setAttr')
            self._command_boxes.append(checkbox)
            self._type_box.layout().addWidget(checkbox)
        
        existing = [cmds.file(ref, q=True, namespace=True) for ref in cmds.file(q=True, reference=True) or []]
        
        self._namespace_menus = []
        namespaces = set()
        for edit in self._edits:
            namespaces.update(edit.namespaces)
        for namespace in sorted(namespaces):
            layout = QtGui.QHBoxLayout()
            layout.addWidget(QtGui.QLabel(namespace))
            combo = QtGui.QComboBox()
            combo.addItem('<None>')
            for name in existing:
                combo.addItem(name)
                if name == namespace:
                    combo.setCurrentIndex(combo.count() - 1)
            layout.addWidget(combo)
            self._namespace_box.layout().addLayout(layout)
    
    def _on_reference(self, *args):
        pass
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
