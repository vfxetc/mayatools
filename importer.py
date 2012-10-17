from __future__ import absolute_import

import os
import re
import difflib
import sys

from PyQt4 import QtCore, QtGui
Qt = QtCore.Qt

from maya import cmds, mel

from sgfs import SGFS

from ks.core.scene_name.core import SceneName
from . import utils


sgfs = SGFS()


def silk(name):
    # __file__ = "$KS_TOOLS/key_base/3d/maya/python/geocache/importer.py"
    # icons = "$KS_TOOLS/key_base/art/icons"
    icons = os.path.abspath(os.path.join(__file__,
        '..', '..', '..', '..', '..',
        'art', 'icons', 'silk'))
    return os.path.join(icons, name + '.png')


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
        if shape is None:
            self._geometry._mapping.pop(self._channel, None)
        else:
            self._geometry._mapping[self._channel] = shape
        self._geometry._custom_mapping = True


class Geometry(QtGui.QWidget):

    def __init__(self, mapping=None, parent=None):
        super(Geometry, self).__init__(parent)
        
        #: Map channels to shapes.
        self._mapping = mapping or {}
        self._custom_mapping = mapping is not None
        
        self._channel_boxes = {}
        
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
        
        button = QtGui.QPushButton(silk_icon('arrow_switch', 12), "Edit")
        button.clicked.connect(self._on_mapping_clicked)
        button.setFixedSize(button.sizeHint().boundedTo(QtCore.QSize(1000, 22)))
        self._main_layout.addWidget(button)
        
        button = QtGui.QPushButton(silk_icon('delete', 12), "Delete")
        button.clicked.connect(self._on_delete)
        button.setFixedSize(button.sizeHint().boundedTo(QtCore.QSize(1000, 22)))
        self._main_layout.addWidget(button)
        
        # Finally setup the mapping UI. This requires self.meshes() to work.
        self._cache_changed()
    
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
    
    def _cache_changed(self):
        self._setup_mapping_ui()
    
    def _auto_match(self):
        
        # Only do this something has been custom done.
        if self._custom_mapping:
            return
        
        cache_path = self.parent().cachePath()
        channels = utils.get_cache_channels(cache_path)
        meshes = utils.get_point_counts(self.meshes())
        
        # Automatically select exact matches.
        for channel, channel_size in channels:
            for mesh, mesh_size in meshes:
                if channel_size != mesh_size and channel_size is not None:
                    continue
                if utils.simple_name(mesh) == utils.simple_name(channel):
                    self._mapping[channel] = mesh
                    break
    
    def _on_fuzzy_match(self, button=None, channels=None):
        
        self._custom_mapping = True
        if channels is None:
            channels = self.parent().channels()
        
        cache_path = self.parent().cachePath()
        channel_sizes = dict(utils.get_cache_channels(cache_path))
        meshes = utils.get_point_counts(self.meshes())
            
        changed = False
        for channel in channels:
            channel_size = channel_sizes.get(channel)
            combobox = self._channel_boxes[channel]
            best = (0, None)
            for mesh, mesh_size in meshes:
                if channel_size != mesh_size and channel_size is not None:
                    continue 
                if utils.simple_name(mesh) == utils.simple_name(channel):
                    self._mapping[channel] = mesh
                    combobox.selectWithData("shape", mesh)
                    break
                ratio = difflib.SequenceMatcher(None, mesh, channel).ratio()
                if ratio > best[0]:
                    best = (ratio, mesh)
            else:
                if best[1] is not None:
                    self._mapping[channel] = best[1]
                    combobox.selectWithData("shape", best[1])
    
    def _on_unlink(self, button=None, channels=None):
        self._custom_mapping = True
        if channels is None:
            channels = self.parent().channels()
        changed = False
        for channel in channels:
            combobox = self._channel_boxes[channel]
            if self._mapping.pop(channel, None):
                combobox.setCurrentIndex(0)
    
    def _node_display_name(self, node):
        return node.rsplit('|', 1)[-1]
    
    def _setup_mapping_ui(self):
        
        self._auto_match()
        self._channel_boxes = {}
        
        # Easiest way to destroy a layout and all of it's children: transfer
        # the layout to another widget that is immediately garbage collected.
        if self._mapping_box.layout():
            QtGui.QWidget().setLayout(self._mapping_box.layout())
        
        layout = QtGui.QGridLayout()
        layout.setColumnStretch(4, 1)
        layout.setVerticalSpacing(1)
        self._mapping_box.setLayout(layout)
        
        cache_path = self.parent().cachePath()
        channels = utils.get_cache_channels(cache_path)
        
        shapes = dict(utils.get_point_counts(self.meshes()))
        
        def button_row(channel=None):
            row = QtGui.QWidget()
            row.setLayout(QtGui.QHBoxLayout())
            row.layout().setContentsMargins(0, 0, 0, 0)
            row.layout().setSpacing(1)
            
            label = '"%s"' % channel if channel else 'All'
            button = QtGui.QPushButton(silk_icon('arrow_refresh', 12), 'Fuzz')
            button.setFixedSize(button.sizeHint().boundedTo(QtCore.QSize(1000, 20)))
            button.setToolTip('Fuzzy Match %s' % label)
            channels = [channel] if channel else None
            button.clicked.connect(lambda *args: self._on_fuzzy_match(channels=channels))
            row.layout().addWidget(button)
            
            button = QtGui.QPushButton(silk_icon('cross', 12), 'Unlink')
            button.setFixedSize(button.sizeHint().boundedTo(QtCore.QSize(1000, 20)))
            button.setToolTip('Unlink %s' % label)
            button.clicked.connect(lambda *args: self._on_unlink(channels=channels))
            row.layout().addWidget(button) 
                       
            return row
            
        if len(channels) > 1:
            layout.addWidget(button_row(), 0, 2)
        
        for row, (channel, channel_point_count) in enumerate(sorted(channels)):
            row += 1
            
            combobox = ChannelMapping(channel=channel, geometry=self)
            combobox.setMaximumHeight(20)
            combobox.addItem('<None>')
            for shape, shape_point_count in sorted(shapes.iteritems()):
                if channel_point_count is not None and channel_point_count != shape_point_count:
                    continue
                if utils.simple_name(channel) == utils.simple_name(shape):
                    combobox.addItem(silk_icon('asterisk_orange', 10), self._node_display_name(shape), dict(shape=shape))
                else:
                    combobox.addItem(self._node_display_name(shape), dict(shape=shape))
            
            self._channel_boxes[channel] = combobox
            
            cautions = []
            
            # Reselect the old mapping, and add a "missing" item if we can't
            # find it.
            selected = self._mapping.get(channel)
            if not combobox.selectWithData('shape', self._mapping.get(channel)) and selected:
                cautions.append('Shape "%s" does not exist' % selected)
                combobox.addItem(selected + ' (missing)', dict(shape=selected))
                combobox.selectWithData('shape', selected)
            
            layout.addWidget(QtGui.QLabel(self._node_display_name(channel) + ':'), row, 0, alignment=Qt.AlignRight)
            layout.addWidget(combobox, row, 1)
            
            layout.addWidget(button_row(channel), row, 2)
            
            if cautions:
                icon = silk_widget('error', 12, '; '.join(cautions))
            else:
                icon = None
            if icon is not None:
                layout.addWidget(icon, row, 3)
        
        
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
            namespace = utils.get_reference_namespace(reference)
            namespace_label = '%s: ' % namespace if namespace else ''
            self._combobox.addItem('%s%s' % (namespace_label, os.path.basename(reference)), dict(
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
        
        button = QtGui.QPushButton(silk_icon("arrow_refresh", 12), "Update")
        button.clicked.connect(self._on_update)
        button.setFixedSize(button.sizeHint().boundedTo(QtCore.QSize(1000, 20)))
        self._main_layout.addWidget(button)
        
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
        
        self._cache_browse_button = QtGui.QPushButton(silk_icon('folder', 12), "Browse")
        self._cache_browse_button.setMaximumSize(QtCore.QSize(75, 20))
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
        
        button = QtGui.QPushButton(silk_icon('link_add', 12), "Add Reference Link")
        button.clicked.connect(self._on_add_reference_link)
        button.setMaximumHeight(22)
        button_layout.addWidget(button)
        
        button = QtGui.QPushButton(silk_icon('link_add', 12), "Add Selection Link")
        button.clicked.connect(self._on_add_selection_link)
        button.setMaximumHeight(22)
        button_layout.addWidget(button)
        
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
        
        self._entity_combo.clear()
        
        workspace = cmds.workspace(q=True, directory=True)
        tasks = sgfs.entities_from_path(workspace)
        if not tasks or tasks[0]['type'] != 'Task':
            cmds.warning('Workspace does not have any tasks; %r -> %r' % (workspace, tasks))
            self._entity_combo.addItem('Custom')
            return
        
        task = tasks[0]
        entity = task.parent()
        entities = []
        
        # Populate shot combo with all reuses that match the current workspace.
        if entity['type'] == 'Shot':
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
        
        self._step_combo.clear()
        
        data = self._entity_combo.currentData()
        if not data:
            return
        entity_paty, entity = data['path'], data['entity']
        
        steps = set()
        for task_path, task in sgfs.entities_in_directory(entity_paty, 'Task', load_tags=None):
            
            # Only add one of every step.
            step = task['step']['code']
            if step in steps:
                continue
            steps.add(step)
            
            self._step_combo.addItem(step, (task_path, ))
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
        
        self._cache_combo.clear()
        self._cache_combo.addItem('Select...')
        
        data = self._step_combo.currentData()
        if not data:
            return
        task_path = data[0]
        
        for geo_cache_name in ('geocache', 'geo_cache', 'geoCache'):
            path = os.path.join(task_path, 'maya', 'data', geo_cache_name)
            if os.path.exists(path):
                for name in os.listdir(path):
                    self._cache_combo.addItem(name, dict(path=os.path.join(path, name), name=name))
        
        # Select the most recent version/revision.
        def get_version(index):
            name = self._cache_combo.itemText(index)
            m = re.search('v(\d+)(?:_r(\d+))?', name)
            if m:
                key = tuple(int(x or 0) for x in m.groups()) + (name, )
                return key
            return (0, 0, name)
        highest = max(xrange(self._cache_combo.count()), key=get_version)
        self._cache_combo.setCurrentIndex(highest)
        
        self._populate_object_combo()
    
    def _on_cache_changed(self, index=None):
        if self._cache_combo.itemText(0) == 'Select...':
            if index:
                self._cache_combo.removeItem(0)
            else:
                return
        self._populate_object_combo()
    
    def _populate_object_combo(self):
        
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
            geo._cache_changed()

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
    
    def iterMapping(self):
        channels = set(self.channels())
        for geo in self._geometry:
            # Reverse the mapping direction!
            for channel, shape in geo.mapping().iteritems():
                if channel in channels:
                    yield shape, channel
    
    def _reverse_mapping(self, input_mapping):
        reversed_mappings = []
        for shape, channel in input_mapping.iteritems():
            for mapping in reversed_mappings:
                if channel not in mapping:
                    break
            else:
                mapping = {}
                reversed_mappings.append(mapping)
            mapping[channel] = shape
        return reversed_mappings
    
    def setMapping(self, mapping):
        # The given mapping goes from shapes to channels, but the Geometry
        # objects work on mappings from channels to shapes. This means that we
        # may need to construct several of the same type of Geometry in order to
        # capture all of the state.
        
        # Split the global mapping up into ones that are referenced or are from
        # the local scene.
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
            for reversed_mapping in self._reverse_mapping(mapping):
                geo = Reference(reference=reference, mapping=reversed_mapping, parent=self)
                self._geometry.append(geo)
                self._geometry_layout.addWidget(geo)
        
        if selection:
            for reversed_mapping in self._reverse_mapping(selection):
                print reversed_mapping
                geo = Selection(selection=reversed_mapping.values(), mapping=reversed_mapping, parent=self)
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
        
        mappings = utils.get_existing_cache_mappings()
        
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
        
        print '# Applying...'
        
        # Find the existing stuff.
        path_to_connections = {}
        malformed_transforms = set()
        for cache_node, cache_path, channel, transform, shape in utils.iter_existing_cache_connections():
            # Ignore the malformed ones for now.
            if shape is None:
                if transform not in malformed_transforms:
                    print '# Ignoring existing cache attached to %r' % transform
                malformed_transforms.add(transform)
                continue
            path_to_connections.setdefault(cache_path, []).append((
                cache_node, channel, transform, shape
            ))
        
        original_selection = cmds.ls(sl=True)
        
        # Get all the caches.
        geocaches = {}
        for geocache in self._geocaches:
            cache_path = geocache.cachePath()
            if not cache_path:
                continue
            geocaches[cache_path] = geocache
        
        # We delete as many caches as we can before creating them, because the
        # mel script which does the connections seems to have some issues with
        # naming collisions on the cacheBlend nodes. This has cleaned up as
        # much of the problem as I think that I can without doing the full
        # import ourselves.
        
        # Delete stray caches. Malformed connections won't be in this dict so
        # they will not be destroyed.
        for cache_path, connections in path_to_connections.iteritems():
            if cache_path not in geocaches:
                for cache_node, channel, transform, shape in connections:
                    utils.delete_cache(cache_node)
        
        to_import = []
        to_connect = []
        for cache_path, geocache in geocaches.iteritems():
            # Get the mapping from shapes to channels, and turn it into
            # transforms to channels since we want to treat the potential
            # "Deformed" copy as the same.
            transform_to_channels = {}
            for shape, channel in geocache.iterMapping():
                transform = utils.get_transform(shape)
                to_connect.append(transform)
                transform_to_channels.setdefault(transform, []).append(channel)
            
            # Clean up the existing ones.
            for cache_node, channel, transform, shape in path_to_connections.pop(cache_path, []):
                
                # Leave matching ones alone.
                if channel in transform_to_channels.get(transform, ()):
                    print '# Existing cache OK: %r' % cache_node
                    # Remove it from the channel list.
                    transform_to_channels[transform] = [x for x in transform_to_channels[transform] if x != channel]
                    continue
            
                # Otherwise, delete the existing connection.
                utils.delete_cache(cache_node)
            
            # Schedule new cache connections.
            for transform, channels in transform_to_channels.iteritems():
                # Skip ones which involve malformed transforms.
                if transform in malformed_transforms:
                    continue
                for channel in channels:
                    to_import.append((cache_path, transform, channel))
        
        # Create new connections.
        for cache_path, transform, channel in to_import:
            print '# Connecting: %r to %r' % (transform, channel)
            mel.eval('doImportCacheFile("%s", "Best Guess", {"%s"}, {"%s"})' % (
                cache_path, transform, channel,
            ))
        
        # Create "Render Stats" connections.
        for transform in to_connect:
            shapes = cmds.listRelatives(transform, shapes=True)
            if len(shapes) == 2:
                orig, deformed = shapes
                for name in ('castsShadows', 'receiveShadows', 'motionBlur',
                    'primaryVisibility', 'smoothShading', 'visibleInReflections',
                    'visibleInRefractions', 'doubleSided', 'opposite'
                ):
                    from_attr = orig + '.' + name
                    to_attr = deformed + '.' + name
                    existing = cmds.connectionInfo(to_attr, sourceFromDestination=True)
                    if existing and existing != from_attr:
                        cmds.warning('Unknown connection from %r to %r' % (existing, to_attr))
                        continue
                    if not existing:
                        cmds.connectAttr(from_attr, to_attr)
            else:
                cmds.warning('Expected 2 shapes under %r; found %r' % (transform, shapes))
        
        # Restore selection.
        if original_selection:
            try:
                cmds.select(original_selection, replace=True)
            except ValueError as e:
                cmds.warning('Error while restoring selection: %r' % e)
        else:
            cmds.select(clear=True)


__also_reload__ = [
    'ks.core.scene_name.core',
    'ks.maya.geocache.utils',
]


def __before_reload__():
    # We have to manually clean this, since we aren't totally sure it will
    # always fall out of scope.
    global dialog
    if dialog:
        dialog.close()
        dialog.destroy()
        dialog = None


dialog = None


def run():
    global dialog
    if dialog:
        dialog.close()
    dialog = Dialog()
    dialog.show()
        