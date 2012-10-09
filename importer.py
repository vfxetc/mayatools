from __future__ import absolute_import

import os
import re

from PyQt4 import QtCore, QtGui
Qt = QtCore.Qt

from maya import cmds, mel

from ks.core.scene_name.core import SceneName


def comparison_name(name):
    name = name.rsplit('|', 1)[-1]
    name = name.rsplit(':', 1)[-1]
    if name.lower().endswith('deformed'):
        name = name[:-len('deformed')]
    return name


class Labeled(QtGui.QVBoxLayout):

    def __init__(self, label, widget):
        super(Labeled, self).__init__()
        self._label = QtGui.QLabel(label)
        self.addWidget(self._label)
        self._widget = widget
        self.addWidget(widget)
    
    def setVisible(self, visible):
        self._label.setVisible(visible)
        self._widget.setVisible(visible)

class Link(QtGui.QGroupBox):
    
    def __init__(self, index):
        super(Link, self).__init__() #"Link %d" % index)
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
        
        ## Cache widgets
        
        self._shot_combo = QtGui.QComboBox()
        self._populate_shot_combo()        
        self._shot_combo.currentIndexChanged.connect(self._on_shot_changed)
        self._shot_pair = Labeled("Shot", self._shot_combo)
        self._cache_layout.addLayout(self._shot_pair)
            
        self._step_combo = QtGui.QComboBox()
        self._step_combo.currentIndexChanged.connect(self._on_step_changed)
        self._step_pair = Labeled("Step", self._step_combo)
        self._cache_layout.addLayout(self._step_pair)
        
        self._cache_combo = QtGui.QComboBox()
        self._cache_combo.currentIndexChanged.connect(self._on_cache_changed)
        self._cache_pair = Labeled("Geocache", self._cache_combo)
        self._cache_layout.addLayout(self._cache_pair)
        
        self._object_combo = QtGui.QComboBox()
        self._object_combo.currentIndexChanged.connect(self._on_object_changed)
        self._object_pair = Labeled("Object", self._object_combo)
        self._cache_layout.addLayout(self._object_pair)
        
        self._cache_field = QtGui.QLineEdit()
        self._cache_field.editingFinished.connect(self._populate_reference_combo)
        self._cache_field_pair = Labeled("Path to Custom Geocache", self._cache_field)
        self._cache_layout.addLayout(self._cache_field_pair)
        
        self._cache_browse_button = QtGui.QPushButton("Browse")
        self._cache_browse_button.setMaximumSize(QtCore.QSize(50, 20))
        self._cache_browse_button.clicked.connect(self._on_cache_browse)
        self._cache_browse_button_pair = Labeled("", self._cache_browse_button)
        self._cache_layout.addLayout(self._cache_browse_button_pair)
        
        self._on_shot_changed()
        
        ## Reference widgets
        
        self._reference_combo = QtGui.QComboBox()
        self._populate_reference_combo()
        self._reference_combo.currentIndexChanged.connect(self._on_reference_changed)
        self._reference_combo_pair = Labeled("Reference", self._reference_combo)
        self._reference_layout.addLayout(self._reference_combo_pair)
        
        self._selection_field = QtGui.QLineEdit()
        self._selection_field_pair = Labeled("Geometry", self._selection_field)
        self._reference_layout.addLayout(self._selection_field_pair)
        
        self._set_selection_button = QtGui.QPushButton("Set to Selection")
        self._set_selection_button.setMaximumSize(
            self._set_selection_button.sizeHint().boundedTo(QtCore.QSize(1000, 20))
        )
        self._set_selection_button.clicked.connect(self._on_set_clicked)
        self._set_selection_button_pair = Labeled("", self._set_selection_button)
        self._reference_layout.addLayout(self._set_selection_button_pair)
        
        self._clear_button = QtGui.QPushButton('Clear')
        self._clear_button.setMaximumSize(QtCore.QSize(50, 20))
        self._clear_button.clicked.connect(self._on_clear_clicked)
        self._clear_button_pair = Labeled("", self._clear_button)
        self._reference_layout.addLayout(self._clear_button_pair)
        
        self._on_reference_changed()
    
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
        
        self._cache_field_pair.setVisible(is_custom)
        self._cache_browse_button_pair.setVisible(is_custom)
        
        self._step_pair.setVisible(not is_custom)
        self._cache_pair.setVisible(not is_custom)
        self._object_pair.setVisible(not is_custom)
        
        if is_custom:
            self._populate_reference_combo()
        else:
            self._populate_step_combo()
            self._on_step_changed()
    
    def _on_step_changed(self, index=None):
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
        
        if self._cache_combo.itemText(0) == 'Select...':
            if index:
                self._cache_combo.removeItem(0)
            else:
                return
        self._populate_object_combo()
        
    
    def _populate_object_combo(self):
        
        cache = str(self._cache_combo.currentText())
        self._object_combo.clear()
        
        if not cache:
            return
        
        # TODO: Do this with SGFS.
        path = cmds.workspace(q=True, directory=True)
        path = path[:path.find(self._current_shot)] + str(self._shot_combo.currentText())
        path = os.path.join(path, str(self._step_combo.currentText()), 'maya', 'data', 'geo_cache', cache)
        if os.path.exists(path):
            for name in os.listdir(path):
                self._object_combo.addItem(name)
    
    def _on_object_changed(self, index=None):
        last_ref = str(self._reference_combo.currentText())
        self._populate_reference_combo(last_ref)
    
    def cachePath(self):
        workspace = cmds.workspace(q=True, directory=True)
        shot = str(self._shot_combo.currentText())
        
        if shot == 'Custom':
            path = os.path.join(workspace, str(self._cache_field.text()))
        
        else:
            step = str(self._step_combo.currentText())
            cache = str(self._cache_combo.currentText())
            name = str(self._object_combo.currentText())
            if not (shot and step and cache and name):
                return
            path = workspace[:workspace.find(self._current_shot)] + shot
            path = os.path.join(path, step, 'maya', 'data', 'geo_cache', cache, name, name + '.xml')
        
        if not os.path.exists(path):
            cmds.warning('Could not find cache: %r' % path)
            return
        
        return path
    
    def setCachePath(self, path):
        self._shot_combo.setCurrentIndex(self._shot_combo.count() - 1)
        self._cache_field.setText(path)
    
    def _populate_reference_combo(self, select="Custom"):
        self._reference_combo.clear()
        
        cache_path = self.cachePath()
        channels = cmds.cacheFile(
            query=True,
            fileName=cache_path,
            channelName=True,
        ) if cache_path else None
        
        print cache_path
        print channels
        
        if channels is not None:
            channels = [x.split(':')[-1] for x in channels]
            references = cmds.file(q=True, reference=True)
            for reference in references:
                raw_nodes = cmds.referenceQuery(reference, nodes=True)
                nodes = set(comparison_name(x) for x in raw_nodes)
                if all(comparison_name(x) in nodes for x in channels):
                    namespace = raw_nodes[0].rsplit(':', 1)[0]
                    self._reference_combo.addItem(namespace, reference)
        
        self._reference_combo.addItem("Custom")
    
    def _on_reference_changed(self, index=None):
        namespace = str(self._reference_combo.currentText())
        reference = str(self._reference_combo.itemData(index).toString()) if index is not None else None
        print 'reference', namespace, reference
        
        is_custom = namespace == 'Custom'
        self._selection_field_pair.setVisible(is_custom)
        self._set_selection_button_pair.setVisible(is_custom)
        
        # self._selection_field.updateGeometry()
        # self._set_selection_button.updateGeometry()
        # self.updateGeometry()
        # #self.adjustSize()
        # #self.layout().update()
        # #self.repaint()
    
    def getSelection(self):
        namespace = str(self._reference_combo.currentText())
        index = self._reference_combo.currentIndex()
        reference = str(self._reference_combo.itemData(index).toString()) if index is not None else None
        is_custom = namespace == 'Custom'
        if is_custom:
            selection = [x.strip() for x in str(self._selection_field.text()).split(',')]
            selection = [x for x in selection if x]
            return selection
        else:
            return cmds.referenceQuery(reference, nodes=True)
    
    def setSelection(self, selection):
        self._reference_combo.setCurrentIndex(self._reference_combo.count() - 1)
        self._selection_field.setText(', '.join(selection))
    
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
        
        self._populate_reference_combo()
    
    def _on_set_clicked(self):
        self._selection_field.setText(', '.join(cmds.ls(selection=True)))
        
    def _on_clear_clicked(self):
        # Set to "Custom", and clear the selection.
        self._reference_combo.setCurrentIndex(self._reference_combo.count() - 1)
        self._selection_field.setText('')
    

class Dialog(QtGui.QMainWindow):

    def __init__(self):
        super(Dialog, self).__init__()
        self._links = []
        self._init_ui()
        self._populate_existing()
    
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
        
        button_layout = QtGui.QHBoxLayout()
        layout.addLayout(button_layout)
        
        self._add_button = button = QtGui.QPushButton("Add Link...")
        button.setMinimumSize(button.sizeHint().expandedTo(QtCore.QSize(100, 0)))
        button_layout.addWidget(button)
        button.clicked.connect(self._on_add_link)
        
        button_layout.addStretch()
        
        self._apply_button = button = QtGui.QPushButton("Apply")
        button.setMinimumSize(button.sizeHint().expandedTo(QtCore.QSize(100, 0)))
        button_layout.addWidget(button)
        button.clicked.connect(self._on_apply_clicked)
        self._save_button = button = QtGui.QPushButton("Save")
        button.setMinimumSize(button.sizeHint().expandedTo(QtCore.QSize(100, 0)))
        button_layout.addWidget(button)
        button.clicked.connect(self._on_save_clicked)
        
        layout.addStretch()
    
    def _populate_existing(self):
        
        switches = cmds.ls(type="historySwitch")
        for switch in switches:
            print 'switch', switch
            cache = None
            selection = []
            for connection in cmds.listConnections(switch, source=True):
                type_ = cmds.nodeType(connection)
                print '\t', type_, connection
                if type_ == 'cacheFile':
                    cache = cmds.cacheFile(connection, q=True, fileName=True)[0]
                elif type_ in ('mesh', 'transform'):
                    selection.append(connection)
            
            print 'CACHE', repr(cache)
            print 'SELECTION', selection
            if not cache or not selection:
                continue
            
            link = Link(self._scroll_layout.count() - 1)
            link.setCachePath(cache)
            link.setSelection(selection)
            
            self._links.append(link)
            self._scroll_layout.insertWidget(self._scroll_layout.count() - 2, link)
            
        self._on_add_link()
    
    def _on_add_link(self):
        link = Link(self._scroll_layout.count() - 1)
        self._links.append(link)
        self._scroll_layout.insertWidget(self._scroll_layout.count() - 2, link)
    
    def _on_save_clicked(self):
        self._on_apply_clicked()
        self.close()
    
    def _on_apply_clicked(self):
        original_selection = cmds.ls(sl=True)
        for link in self._links:
            cache = link.cachePath()
            selection = link.getSelection()
            print link
            print cache
            
            if not selection:
                continue
            
            # Delete existing caches.
            history = cmds.listHistory(selection, levels=2)
            caches = []
            for node in history:
                if cmds.nodeType(node) == 'cacheFile':
                    caches.append(node)
            print 'existing caches', caches
            if caches:
                caches = list(set(caches))
                if len(caches) == 1 and cmds.cacheFile(caches[0], q=True, fileName=True)[0] == cache:
                    print 'this is already ok; leave it alone'
                    continue
                else:
                    mel.eval('deleteCacheFile(3, {"keep", "%s", "geometry"})' % (
                        ','.join(caches),
                    ))
                
            
            # When a cache is created Maya creates a new shape node with
            # "Deformed" appended to it. When the cache is deleted, Maya does
            # not restore the network to it's original state, so the shapeNode
            # is still named deformed. Trying to re-cache once this has
            # happened breaks the import as the expected names have changed
            # from the export. To avoid this, the transform node is always
            # selected instead of the shape. The shape node is whats exported
            # in the original cache.
            cmds.select(clear=True)
            for name in selection:
                type_ = cmds.nodeType(name)
                if type_ == 'mesh':
                    cmds.select(cmds.listRelatives(name, parent=True)[0])
                elif type_ == 'transform':
                    cmds.select(name)
                
            channels = set(x.split(':')[-1] for x in cmds.cacheFile(
                query=True,
                fileName=cache,
                channelName=True,
            ) or [])
            print channels
            print cmds.ls(sl=True)
            
            # mel.eval("source doImportCacheFile.mel")
            mel.eval('doImportCacheFile("%s", "Best Guess", {}, {})' % (
                cache,
                # ', '.join('"%s"' % x for x in selection),
            ))
            
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
        