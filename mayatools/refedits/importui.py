import os
import re
import collections
import traceback

from PyQt4 import QtCore, QtGui
Qt = QtCore.Qt

from maya import cmds, mel

from sgfs.ui import product_select
import sgfs.ui.scene_name.widget as scene_name


RefEdit = collections.namedtuple('RefEdit', ('command', 'namespaces', 'nodes', 'source'))


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
        
        self._option_box = QtGui.QGroupBox("Options")
        self._option_box.setLayout(QtGui.QVBoxLayout())
        self.layout().addWidget(self._option_box)
        
        self._only_selected_checkbox = QtGui.QCheckBox("Only Apply to Selected Nodes", checked=True)
        self._only_selected_checkbox.stateChanged.connect(lambda state: self._path_changed(self._path))
        self._option_box.layout().addWidget(self._only_selected_checkbox)

        self._node_box = QtGui.QGroupBox("Nodes")
        self._node_box.setLayout(QtGui.QVBoxLayout())
        self.layout().addWidget(self._node_box)

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
            nodes = re.findall(r'(\|[\|:\w]+)', line)
            self._edits.append(RefEdit(
                command=command,
                nodes=set(nodes),
                namespaces=set(namespaces),
                source=line,
            ))
            
        
    def _path_changed(self, path):
        
        self._path = path

        for child in self._type_box.children():
            if isinstance(child, QtGui.QWidget):
                child.hide()
                child.destroy()
        for child in self._node_box.children():
            if isinstance(child, QtGui.QWidget):
                child.hide()
                child.destroy()
            
        if path is None:
            self._type_box.layout().addWidget(QtGui.QLabel("Nothing"))
            self._option_box.layout().addWidget(QtGui.QLabel("Nothing"))
            return
        
        self._parse_file(path)
        
        self._command_boxes = []
        for command in sorted(set(e.command for e in self._edits)):
            checkbox = QtGui.QCheckBox(command)
            checkbox.setChecked(command == 'setAttr')
            self._command_boxes.append(checkbox)
            self._type_box.layout().addWidget(checkbox)
        
        self._node_boxes = []
        all_nodes = set()
        for e in self._edits:
            all_nodes.update(e.nodes)

        if self._only_selected_checkbox.isChecked():
            all_nodes.intersection_update(cmds.ls(selection=True, long=True))

        for node in sorted(all_nodes):
            checkbox = QtGui.QCheckBox(node, checked=True)
            self._node_boxes.append(checkbox)
            self._node_box.layout().addWidget(checkbox)

        # existing = [cmds.file(ref, q=True, namespace=True) for ref in cmds.file(q=True, reference=True) or []]
        # self._namespace_menus = []
        # namespaces = set()
        # for edit in self._edits:
        #     namespaces.update(edit.namespaces)
        # for namespace in sorted(namespaces):
        #     layout = QtGui.QHBoxLayout()
        #     layout.addWidget(QtGui.QLabel(namespace))
        #     combo = QtGui.QComboBox()
        #     combo.addItem('<None>')
        #     for name in existing:
        #         combo.addItem(name)
        #         if name == namespace:
        #             combo.setCurrentIndex(combo.count() - 1)
        #     layout.addWidget(combo)
        #     self._option_box.layout().addLayout(layout)
    
    def _on_reference(self, *args):
        
        do_command = {}
        for checkbox in self._command_boxes:
            do_command[str(checkbox.text())] = checkbox.isChecked()
        do_node = {}
        for checkbox in self._node_boxes:
            do_node[str(checkbox.text())] = checkbox.isChecked()
        
        applied = 0
        failed = 0
        for edit in self._edits:
            
            if not do_command.get(edit.command):
                continue
            if not all(do_node.get(n) for n in edit.nodes):
                continue

            try:
                mel.eval(edit.source)
            except Exception as e:
                cmds.warning(str(e))
                failed += 1
            else:
                applied += 1
        
        (QtGui.QMessageBox.warning if failed else QtGui.QMessageBox.information)(
            self,
            "Applied Reference Edits",
            "Applied %d edits with %d failures." % (applied, failed)
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
    dialog = Dialog()
    dialog.show()
