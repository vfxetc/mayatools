from __future__ import absolute_import

import os
import re

from PyQt4 import QtCore, QtGui
Qt = QtCore.Qt

from maya import cmds, mel

from ks.core.scene_name.core import SceneName
from ks.maya import mcc
from sgfs import SGFS


sgfs = SGFS()


def comparison_name(name):
    name = name.rsplit('|', 1)[-1]
    name = name.rsplit(':', 1)[-1]
    for word in ('deformed', 'orig'):
        if name.lower().endswith(word):
            name = name[:-len(word)]
    return name


def get_transform(input_node, strict=True):
    node = input_node
    while True:
        type_ = cmds.nodeType(node)
        if type_ == 'transform':
            return node
        relatives = cmds.listRelatives(node, parent=True)
        if not relatives:
            if strict:
                raise ValueError('could not find transform for %r' % node)
            return None
        node = relatives[0]


def delete_cache(node):
    print '# Deleting cache:', node
    mel.eval('deleteCacheFile(3, {"keep", "%s", "geometry"})' % node)


def silk(name):
    return '/home/mboers/Documents/icons/silk/icons/%s.png' % name

def silk_icon(name, size=16):
    icon = QtGui.QIcon(silk(name))
    if size != 16:
        icon = QtGui.QIcon(icon.pixmap(size, size))
    return icon


def silk_widget(name, size=16, tooltip=None):
    icon = QtGui.QIcon(silk(name))
    label = QtGui.QLabel()
    label.setPixmap(icon.pixmap(size, size))
    label.setFixedSize(QtCore.QSize(size, size))
    if tooltip:
        label.setToolTip(tooltip)
    return label


class ComboBox(QtGui.QComboBox):
    
    def itemData(self, index):
        data = super(ComboBox, self).itemData(index).toPyObject()
        return self._conform_item_data(data)
    
    def _conform_item_data(self, data):
        if isinstance(data, QtCore.QString):
            return str(data)
        if isinstance(data, dict):
            return dict((self._conform_item_data(k), self._conform_item_data(v)) for k, v in data.iteritems())
        return data
    
    def currentData(self):
        index = self.currentIndex()
        return self.itemData(index)
    
    def indexWithText(self, text):
        for i in xrange(self.count()):
            if self.itemText(i) == text:
                return i
    
    def selectWithText(self, text):
        index = self.indexWithText(text)
        if index is not None:
            self.setCurrentIndex(index)
            return True
    
    def indexWithData(self, key, value):
        for i in xrange(self.count()):
            data = self.itemData(i)
            if data and data.get(key) == value:
                return i
    
    def selectWithData(self, key, value):
        index = self.indexWithData(key, value)
        if index is not None:
            self.setCurrentIndex(index)
            return True


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


class ChannelMapping(ComboBox):

    def __init__(self, channel, geometry):
        super(ChannelMapping, self).__init__()
        self._channel = channel
        self._geometry = geometry
        self.activated.connect(self._on_activated)
    
    def _on_activated(self, index):
        data = self.currentData() or {}
        shape = data.get('shape')
        return
        if shape is None:
            self._geometry._mapping.pop(self._node, None)
        else:
            self._geometry._mapping[self._node] = channel


class Geometry(QtGui.QWidget):

    def __init__(self, mapping=None, parent=None):
        super(Geometry, self).__init__(parent)
        
        #: Map mesh names to channels.
        self._mapping = mapping or {}
        
        self._setup_pre_ui()
        self._setup_ui()
        self._setup_post_ui()
    
    def _setup_pre_ui(self):

        self.setLayout(QtGui.QVBoxLayout())
        
        self._main_layout = QtGui.QHBoxLayout()
        self.layout().addLayout(self._main_layout)
        
        # self._main_layout.addWidget(silk_widget('tick', tooltip='OK'))
        
        self._mapping_box = QtGui.QGroupBox("Channel Mapping")
        self._mapping_box.hide()
        self.layout().addWidget(self._mapping_box)
        
    def _setup_ui(self):
        pass
    
    def _setup_post_ui(self):
        
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.setContentsMargins(0, 0, 0, 0)
        
        self._mapping_button = QtGui.QPushButton(silk_icon('arrow_switch', 12), "Edit")
        self._mapping_button.clicked.connect(self._on_mapping_clicked)
        self._mapping_button.setFixedSize(QtCore.QSize(60, 22))
        self._main_layout.addWidget(self._mapping_button)
        
        self._delete_button = QtGui.QPushButton(silk_icon('delete', 12), "Delete")
        self._delete_button.clicked.connect(self._on_delete)
        self._delete_button.setFixedSize(QtCore.QSize(70, 22))
        self._main_layout.addWidget(self._delete_button)
        
        # Finally setup the mapping UI. This requires self.meshes() to work.
        self._cache_changed(self.parent())
    
    def _on_mapping_clicked(self):
        do_open = self._mapping_box and self._mapping_box.isHidden()
        self._mapping_box.setVisible(do_open)
    
    def _on_delete(self):
        
        # Remove ourselves from our parent.
        self.parent()._geometry.remove(self)
        
        # Remove the widget.
        self.hide()
        self.destroy()
    
    def mapping(self):
        return self._mapping
        
    def meshes(self):
        res = set()
        for node in self.nodes():
            type_ = cmds.nodeType(node)
            if type_ == 'transform':
                shapes = cmds.listRelatives(node, children=True, type="mesh")
                if shapes:
                    res.add(shapes[0])
            elif type_ == 'mesh':
                res.add(node)
        return sorted(res)
    
    def _cache_changed(self, geocache):
        self._channels_changed(geocache.channels())
        self._setup_mapping_ui()
    
    def _channels_changed(self, channels):
        # Automatically select exact matches.
        for mesh in self.meshes():
            if self._mapping.get(mesh) is None:
                for channel in channels:
                    if comparison_name(mesh) == comparison_name(channel):
                        self._mapping[mesh] = channel
                        break
    
    def _node_display_name(self, node):
        return node.rsplit('|', 1)[-1]
    
    def _setup_mapping_ui(self):
        
        # Easiest way to destroy a layout and all of it's children: transfer
        # the layout to another widget that is immediately garbage collected.
        if self._mapping_box.layout():
            QtGui.QWidget().setLayout(self._mapping_box.layout())
        
        layout = QtGui.QGridLayout()
        layout.setColumnStretch(3, 1)
        layout.setVerticalSpacing(1)
        self._mapping_box.setLayout(layout)
        
        cache_path = self.parent().cachePath()
        try:
            channels = mcc.get_channels(cache_path)
        except mcc.ParseError as e:
            cmds.warning('Could not parse MCC for channel data; %r' % e)
            channels = cmds.cacheFile(q=True, fileName=cache_path, channelName=True)
            channels = [(c, None) for c in channels]
        shapes = dict((shape, cmds.getAttr(shape + '.vrts', size=True)) for shape in self.meshes())
        
        for row, (channel, channel_point_count) in enumerate(sorted(channels)):

            combobox = ChannelMapping(channel, self)
            combobox.setMaximumHeight(20)
            combobox.addItem('<None>')
            for shape, shape_point_count in sorted(shapes.iteritems()):
                if channel_point_count is not None and channel_point_count != shape_point_count:
                    continue
                if comparison_name(channel) == comparison_name(shape):
                    combobox.addItem(silk_icon('asterisk_orange', 10), self._node_display_name(shape), dict(shape=shape))
                else:
                    combobox.addItem(self._node_display_name(shape), dict(shape=shape))
            
            cautions = []
            
            # Reselect the old mapping, and add a "missing" item if we can't
            # find it.
            # selected = self._mapping.get(shape)
            # if not combobox.selectWithData('shape', self._mapping.get(shape)) and selected:
            #     cautions.append('Channel "%s" does not exist' % selected)
            #     combobox.addItem(selected + ' (missing)', dict(channel=selected))
            #     combobox.selectWithData('channel', selected)
            
            layout.addWidget(QtGui.QLabel(self._node_display_name(channel) + ':'), row, 0, alignment=Qt.AlignRight)
            layout.addWidget(combobox, row, 1)
            
            if cautions:
                icon = silk_widget('cross', 12, '; '.join(cautions))
            else:
                icon = silk_widget('tick', 12, 'OK')
            layout.addWidget(icon, row, 2)
            
        # For some reason I can't always get the layout to update it, so I force
        # it my adding a hidden label. Please remove this if you can.
        trigger = QtGui.QLabel('')
        layout.addWidget(trigger)
        trigger.hide()


class Reference(Geometry):
    
    def __init__(self, reference=None, mapping=None, parent=None):
        super(Reference, self).__init__(mapping=mapping, parent=parent)
        if reference is not None:
            self.setReference(reference)
    
    def _setup_ui(self):
        
        self._combobox = ComboBox()
        self._populate_combobox()
        self._main_layout.addWidget(self._combobox)
        
        super(Reference, self)._setup_ui()
        
        self._combobox.currentIndexChanged.connect(self._on_combobox_changed)
        self._on_combobox_changed(0)
    
    def reference(self):
        return (self._combobox.currentData() or {}).get('reference')
    
    def setReference(self, reference):
        self._combobox.selectWithData('reference', reference) or self._combobox.addItem(reference)
    
    def _populate_combobox(self):
        for reference in cmds.file(q=True, reference=True) or []:
            namespace = cmds.referenceQuery(reference, namespace=True).strip(':')
            self._combobox.addItem('%s: %s' % (namespace, os.path.basename(reference)), dict(
                namespace=namespace,
                reference=reference,
            ))
    
    def _on_combobox_changed(self, index):
        self._setup_mapping_ui()
    
    def nodes(self):
        reference = self.reference()
        if reference:
            return cmds.referenceQuery(reference, nodes=True, dagPath=True) or []
        else:
            return {}
    
    def _node_display_name(self, node):
        return node.rsplit(':', 1)[-1]


class Selection(Geometry):
    
    def __init__(self, selection=None, mapping=None, parent=None):
        super(Selection, self).__init__(mapping=mapping, parent=parent)
        self.setSelection(selection)
    
    def _setup_ui(self):
                
        self._field = QtGui.QLineEdit()
        self._field.editingFinished.connect(self._on_field_changed)
        self._main_layout.addWidget(self._field)
        
        self._update_button = QtGui.QPushButton("Update")
        self._update_button.clicked.connect(self._on_update)
        self._update_button.setFixedSize(QtCore.QSize(60, 22))
        self._main_layout.addWidget(self._update_button)
        
        super(Selection, self)._setup_ui()
    
    def selection(self):
        selection = [x.strip() for x in str(self._field.text()).split(',')]
        selection = [x for x in selection if x]
        return selection
        
    def setSelection(self, selection):
        self._field.setText(', '.join(selection or []))
        self._setup_mapping_ui()
    
    def _on_field_changed(self):
        self._setup_mapping_ui()
        
    def _on_update(self):
        selection = cmds.ls(sl=True)
        selection = [x for x in selection if cmds.nodeType(x) in ('mesh', 'transform')]
        self.setSelection(selection)
    
    def nodes(self):
        return self.selection()


class Geocache(QtGui.QGroupBox):
    
    def __init__(self):
        super(Geocache, self).__init__()
        
        #: Mapping of shape nodes to channels.
        self._mapping = {}
        
        #: Geometry objects.
        self._geometry = []
        
        self._setup_ui()
    
    def _setup_ui(self):
        
        # Lots of layouts...
        self.setLayout(QtGui.QVBoxLayout())
        
        ## Cache widgets

        self._cache_layout = QtGui.QHBoxLayout()
        self.layout().addLayout(self._cache_layout)
        
        self._entity_combo = ComboBox()
        self._populate_entity_combo()        
        self._entity_combo.activated.connect(self._on_entity_changed)
        self._entity_pair = Labeled("Entity", self._entity_combo)
        self._cache_layout.addLayout(self._entity_pair)
            
        self._step_combo = ComboBox()
        self._step_combo.activated.connect(self._on_step_changed)
        self._step_pair = Labeled("Step", self._step_combo)
        self._cache_layout.addLayout(self._step_pair)
        
        self._cache_combo = ComboBox()
        self._cache_combo.activated.connect(self._on_cache_changed)
        self._cache_pair = Labeled("Cache", self._cache_combo)
        self._cache_layout.addLayout(self._cache_pair)
        
        self._object_combo = ComboBox()
        self._object_combo.activated.connect(self._on_object_changed)
        self._object_pair = Labeled("Object", self._object_combo)
        self._cache_layout.addLayout(self._object_pair)
        
        self._cache_field = QtGui.QLineEdit()
        # self._cache_field.editingFinished.connect(self._populate_reference_combo)
        self._cache_field_pair = Labeled("Path to Custom Geocache", self._cache_field)
        self._cache_layout.addLayout(self._cache_field_pair)
        
        self._cache_browse_button = QtGui.QPushButton("Browse")
        self._cache_browse_button.setMaximumSize(QtCore.QSize(50, 20))
        self._cache_browse_button.clicked.connect(self._on_cache_browse)
        self._cache_browse_button_pair = Labeled("", self._cache_browse_button)
        self._cache_layout.addLayout(self._cache_browse_button_pair)
        
        self._on_entity_changed()
        
        ## Geometry widgets
        
        self.layout().addWidget(QtGui.QLabel("Geometry & References"))
        
        self._geometry_layout = QtGui.QVBoxLayout()
        self.layout().addLayout(self._geometry_layout)
        
        ## Buttons.
        
        button_layout = QtGui.QHBoxLayout()
        self.layout().addLayout(button_layout)
        
        icon = QtGui.QIcon('/home/mboers/Documents/icons/silk/icons/link_add.png')
        icon = QtGui.QIcon(icon.pixmap(12, 12))
        self._link_reference_button = QtGui.QPushButton(icon, "Add Reference Link")
        self._link_reference_button.clicked.connect(self._on_add_reference_link)
        self._link_reference_button.setMaximumHeight(22)
        button_layout.addWidget(self._link_reference_button)
        
        icon = QtGui.QIcon('/home/mboers/Documents/icons/silk/icons/link_add.png')
        icon = QtGui.QIcon(icon.pixmap(12, 12))
        self._link_selection_button = QtGui.QPushButton(icon, "Add Selection Link")
        self._link_selection_button.clicked.connect(self._on_add_selection_link)
        self._link_selection_button.setMaximumHeight(22)
        button_layout.addWidget(self._link_selection_button)
        
        button_layout.addStretch()
        
        # Mappings.
        self._mapping_layout = QtGui.QFormLayout()
        self.layout().addLayout(self._mapping_layout)
        
    def _on_add_reference_link(self):
        geo = Reference(parent=self)
        self._geometry.append(geo)
        self._geometry_layout.addWidget(geo)
    
    def _on_add_selection_link(self):
        geo = Selection(parent=self)
        geo._on_update()
        self._geometry.append(geo)
        self._geometry_layout.addWidget(geo)
    
    def _populate_entity_combo(self):
        print '# _populate_entity_combo'
        
        self._entity_combo.clear()
        
        workspace = cmds.workspace(q=True, directory=True)
        tasks = sgfs.entities_from_path(workspace)
        if not tasks or tasks[0]['type'] != 'Task':
            cmds.warning('Workspace does not have any tasks; %r -> %r' % (workspace, tasks))
            self._entity_combo.addItem('Custom')
            return
        
        task = tasks[0]
        entity = task.parent()
        
        # Populate shot combo with all reuses that match the current workspace.
        if entity['type'] == 'Shot':
            entities = []
            seq = entity.parent()
            seq_path = sgfs.path_for_entity(seq)
            for shot_path, shot in sgfs.entities_in_directory(seq_path, "Shot", load_tags=None):
                if shot.fetch('code').startswith(entity.fetch('code')[:6]):
                    entities.append((
                        shot['code'], shot_path, shot
                    ))
        
        elif entity['type'] == 'Asset':
            entities.append((
                entity['code'], sgfs.path_for_entity(entity), entity
            ))
        
        else:
            cmds.warning('Cannot extract entities from %r' % entity)
        
        for name, path, entity in entities:
            self._entity_combo.addItem(name, dict(
                name=name,
                path=path,
                entity=entity
            ))
        self._entity_combo.addItem('Custom')
        
    def _populate_step_combo(self):
        print '# _populate_step_combo'
        
        self._step_combo.clear()
        
        data = self._entity_combo.currentData()
        if not data:
            return
        entity_paty, entity = data['path'], data['entity']
        
        for task_path, task in sgfs.entities_in_directory(entity_paty, 'Task', load_tags=None):
            self._step_combo.addItem(task['step']['code'], (task_path, task))
            if task['step']['code'].lower().startswith('anim'):
                self._step_combo.setCurrentIndex(self._step_combo.count() - 1)

    def _on_entity_changed(self, index=None):
        
        shot = self._entity_combo.currentData()
        is_custom = shot is None
        
        self._cache_field_pair.setVisible(is_custom)
        self._cache_browse_button_pair.setVisible(is_custom)
        
        self._step_pair.setVisible(not is_custom)
        self._cache_pair.setVisible(not is_custom)
        self._object_pair.setVisible(not is_custom)
        
        if is_custom:
            pass
            # self._populate_reference_combo()
        else:
            self._populate_step_combo()
            self._on_step_changed()
    
    def _on_step_changed(self, index=None):
        self._populate_cache_combo()
        
    def _populate_cache_combo(self):
        print '# _populate_cache_combo'
        
        self._cache_combo.clear()
        self._cache_combo.addItem('Select...')
        
        data = self._step_combo.currentData()
        if not data:
            return
        task_path, task = data
        
        for geo_cache_name in ('geocache', 'geo_cache', 'geoCache'):
            path = os.path.join(task_path, 'maya', 'data', geo_cache_name)
            if os.path.exists(path):
                for name in os.listdir(path):
                    self._cache_combo.addItem(name, dict(path=os.path.join(path, name), name=name))
        
        self._populate_object_combo()
    
    def _on_cache_changed(self, index=None):
        if self._cache_combo.itemText(0) == 'Select...':
            if index:
                self._cache_combo.removeItem(0)
            else:
                return
        self._populate_object_combo()
    
    def _populate_object_combo(self):
        print '# _populate_object_combo'
        
        previous = self._object_combo.currentData() or {}
        
        self._object_combo.clear()
        
        data = self._cache_combo.currentData()
        if not data:
            return
        path, name = data['path'], data['name']
        
        if os.path.exists(path):
            for name in os.listdir(path):
                obj_path = os.path.join(path, name)
                self._object_combo.addItem(name, dict(path=obj_path, name=name))
                if obj_path == previous.get('path'):
                    self._object_combo.setCurrentIndex(self._object_combo.count() - 1)
        
        current = self._object_combo.currentData()
        if not current:
            self._object_combo.setCurrentIndex(self._object_combo.count() - 1)
            current = self._object_combo.currentData() or {}
        if not previous.get('path') or previous.get('path') != current.get('path'):
            self._on_object_changed()
    
    def _on_object_changed(self, index=None):
        for geo in self._geometry:
            geo._cache_changed(self)

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
        
    def cachePath(self):
        
        workspace = cmds.workspace(q=True, directory=True)
        entity_data = self._entity_combo.currentData()
                
        if not entity_data:
            relative = str(self._cache_field.text())
            if not relative:
                return
            path = os.path.join(workspace, relative)
        
        else:
            data = self._object_combo.currentData()
            if not data:
                return None
            path, name = data['path'], data['name']
            path = os.path.join(path, name + '.xml')
        
        if not os.path.exists(path):
            cmds.warning('Could not find cache: %r' % path)
            return
        
        return path
    
    def setCachePath(self, path):
        
        # If we can seperate all the data out, then do so.
        entities = sgfs.entities_from_path(path)
        if entities and entities[0]['type'] == 'Task':
            task = entities[0]
            shot = task.parent()
            if shot['type'] == 'Shot':
                task_path = sgfs.path_for_entity(task)
                relative = os.path.relpath(path, task_path)
                m = re.match(r'maya/data/(geocache|geo_cache|geoCache)/(\w+)/(\w+)/\3.xml', relative)
                if m:
                    _, cache_name, object_name = m.groups()
                    shot_i = self._entity_combo.indexWithText(shot['code'])
                    if shot_i is None:
                        self._entity_combo.insertItem(0, shot['code'], (sgfs.path_for_entity(shot), shot))
                        shot_i = 0
                    # Assume that the combos automatically trigger the next
                    # the automatically populate.
                    self._entity_combo.setCurrentIndex(shot_i)
                    self._populate_step_combo()
                    self._step_combo.setCurrentIndex(self._step_combo.indexWithText(task['step']['code']))
                    self._populate_cache_combo()
                    self._cache_combo.setCurrentIndex(self._cache_combo.indexWithText(cache_name))
                    self._populate_object_combo()
                    self._object_combo.setCurrentIndex(self._object_combo.indexWithText(object_name))
                    return
        
        self._entity_combo.setCurrentIndex(self._entity_combo.count() - 1)
        self._on_entity_changed()
        workspace = cmds.workspace(q=True, directory=True)
        relative = os.path.relpath(path, workspace)
        if relative.startswith('.'):
            self._cache_field.setText(path)
        else:
            self._cache_field.setText(relative)
    
    def channels(self):
        cache_path = self.cachePath()
        if not cache_path:
            return []
        else:
            return cmds.cacheFile(q=True, fileName=cache_path, channelName=True) or []
    
    def mapping(self):
        channels = set(self.channels())
        mapping = dict()
        for geo in self._geometry:
            mapping.update((k, v) for k, v in geo.mapping().iteritems() if v in channels)
        return mapping
    
    def setMapping(self, mapping):
        
        references = {}
        selection = {}
        for shape, channel in mapping.iteritems():
            try:
                reference = cmds.referenceQuery(shape, filename=True)
            except RuntimeError:
                selection[shape] = channel
            else:
                references.setdefault(reference, {})[shape] = channel
        
        for reference, mapping in sorted(references.iteritems()):
            geo = Reference(reference=reference, mapping=mapping, parent=self)
            self._geometry.append(geo)
            self._geometry_layout.addWidget(geo)
        
        if selection:
            geo = Selection(selection=selection.keys(), mapping=selection, parent=self)
            self._geometry.append(geo)
            self._geometry_layout.addWidget(geo)


class Dialog(QtGui.QDialog):

    def __init__(self):
        super(Dialog, self).__init__()
        self._geocaches = []
        self._init_ui()
        self._populate_existing()
    
    def _init_ui(self):
        self.setWindowTitle('Geocache Import')
        self.setWindowFlags(Qt.Tool)
        self.setMinimumWidth(900)
        self.setMinimumHeight(550)
        
        main_layout = QtGui.QVBoxLayout()
        self.setLayout(main_layout)
        
        self._scroll_widget = area = QtGui.QScrollArea()
        main_layout.addWidget(area)
        area.setFrameShape(QtGui.QFrame.NoFrame)
        area.setWidgetResizable(True)
                
        area_widget = QtGui.QWidget()
        area.setWidget(area_widget)
        self._scroll_layout = QtGui.QVBoxLayout()
        area_widget.setLayout(self._scroll_layout)
        self._scroll_layout.addStretch()
        
        button_layout = QtGui.QHBoxLayout()
        main_layout.addLayout(button_layout)
        
        self._link_button = button = QtGui.QPushButton("Add Geocache...")
        button.setMinimumSize(button.sizeHint().expandedTo(QtCore.QSize(100, 0)))
        button_layout.addWidget(button)
        button.clicked.connect(self._on_add_geocache)
        
        button_layout.addStretch()
        
        self._apply_button = button = QtGui.QPushButton("Apply")
        button.setMinimumSize(button.sizeHint().expandedTo(QtCore.QSize(100, 0)))
        button_layout.addWidget(button)
        button.clicked.connect(self._on_apply_clicked)
        self._save_button = button = QtGui.QPushButton("Save")
        button.setMinimumSize(button.sizeHint().expandedTo(QtCore.QSize(100, 0)))
        button_layout.addWidget(button)
        button.clicked.connect(self._on_save_clicked)
        
    
    def _populate_existing(self):
        
        mappings = {}
        cache_nodes = cmds.ls(type='cacheFile') or []
        for cache_node in cache_nodes:
            cache_path = cmds.cacheFile(cache_node, q=True, fileName=True)[0]
            mapping = mappings.setdefault(cache_path, {})
            
            ## Identify what it is connected to.
            
            channel = cmds.getAttr(cache_node + '.channel[0]')
            
            switch = cmds.listConnections(cache_node + '.outCacheData[0]')
            if not switch:
                cmds.warning('Could not find switch for %r' % cache_node)
                continue
            switch = switch[0]
            switch_type = cmds.nodeType(switch)
            if switch_type != 'historySwitch':
                cmds.warning('Unknown cache node layout; found %s %r' % (switch_type, switch))
                continue
            
            transform = cmds.listConnections(switch + '.outputGeometry[0]')[0]
            shapes = cmds.listRelatives(transform, children=True, shapes=True)
            if len(shapes) == 2 and comparison_name(shapes[0]) == comparison_name(shapes[1]):
                shapes = [shapes[0]]
            if len(shapes) != 1:
                cmds.warning('Could not identify single shape connected to cache; found %r' % shapes)
                continue
            shape = shapes[0]
            
            mapping[shape] = channel
        
        for cache_path, mapping in sorted(mappings.iteritems()):
            if not mapping:
                continue
        
            geocache = Geocache()
            geocache.setCachePath(cache_path)
            geocache.setMapping(mapping)
            
            self._geocaches.append(geocache)
            self._scroll_layout.insertWidget(self._scroll_layout.count() - 1, geocache)
        
        if not self._geocaches:
            self._on_add_geocache()
    
    def _on_add_geocache(self):
        geocache = Geocache()
        self._geocaches.append(geocache)
        self._scroll_layout.insertWidget(self._scroll_layout.count() - 1, geocache)
    
    def _on_save_clicked(self):
        self._on_apply_clicked()
        self.close()
    
    def _on_apply_clicked(self):
        print 'APPLY'
        
        # Lookup all cacheFile nodes, and create a dict mapping from the XML
        # file to the nodes which use it.
        cache_nodes = cmds.ls(type='cacheFile') or []
        path_to_cache_nodes = {}
        for node in cache_nodes:
            path = cmds.cacheFile(node, q=True, fileName=True)[0]
            path_to_cache_nodes.setdefault(path, []).append(node)
        
        original_selection = cmds.ls(sl=True)
        for geocache in self._geocaches:
            
            cache_path = geocache.cachePath()
            if not cache_path:
                continue
            
            mapping = geocache.mapping()
            transforms = dict((get_transform(mesh), mesh) for mesh in mapping)
            if len(mapping) != len(transforms):
                cmds.warning('Meshes and transforms are not 1 to 1.')
            
            for cache_node in path_to_cache_nodes.get(cache_path, []):
                
                # Identify what it is connected to.
                channel = cmds.getAttr(cache_node + '.channel[0]')
                switch = cmds.listConnections(cache_node + '.outCacheData[0]')
                if not switch:
                    cmds.warning('Could not find switch for %r' % cache_node)
                    delete_cache(cache_node)
                    continue
                switch = switch[0]
                
                switch_type = cmds.nodeType(switch)
                if switch_type != 'historySwitch':
                    cmds.warning('Unknown cache node layout; found %s %r' % (switch_type, switch))
                    delete_cache(cache_node)
                    continue
                
                node = cmds.listConnections(switch + '.outputGeometry[0]')[0]
                transform = get_transform(node)
                
                # Leave it alone (and remove it from the mapping) if it is
                # already setup.
                if mapping.get(transforms.get(transform)) == channel:
                    print '# Existing cache OK: %r to %r via %r' % (cache_node, transform, channel)
                    mapping.pop(transforms[transform])
                    continue
            
                # Delete existing cache nodes.
                delete_cache(cache_node)
            
            # Connect new caches.
            for mesh, channel in mapping.iteritems():
                print '# Connecting: %r to %r' % (mesh, channel)
                mel.eval('doImportCacheFile("%s", "Best Guess", {"%s"}, {"%s"})' % (
                    cache_path, get_transform(mesh), channel,
                ))
        
        # Restore selection.
        if original_selection:
            cmds.select(original_selection, replace=True)
        else:
            cmds.select(clear=True)


__also_reload__ = [
    'ks.core.scene_name.core',
    'ks.maya.mcc',
]


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
        