from __future__ import absolute_import

import os

from uitools.qt import QtGui

from maya import cmds

import sgpublish.exporter.maya
import sgpublish.exporter.ui.publish.maya
import sgpublish.exporter.ui.tabwidget
import sgpublish.exporter.ui.workarea
import sgpublish.uiutils


class RefEditExporter(sgpublish.exporter.maya.Exporter):

    def __init__(self):
        filename = cmds.file(q=True, sceneName=True) or 'refedits'
        filename_hint = os.path.splitext(filename)[0] + '.mel'
        super(RefEditExporter, self).__init__(
            workspace=cmds.workspace(q=True, fullName=True) or None,
            filename_hint=filename_hint,
            publish_type='maya_reference_edits',
        )
    
    def export_publish(self, publisher, **kwargs):
        
        # Construct a path.
        path = os.path.join(publisher.directory, os.path.basename(self.filename_hint))
        
        # Set the primary path (on Shotgun)
        publisher.path = path
        
        return self.export(publisher.directory, path, **kwargs)
        
    def export(self, directory, path, references):
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(path, 'w') as fh:
            for ref in references:
                fh.write('// %s\n' % ref)
                for edit in cmds.referenceQuery(ref, editStrings=True) or []:
                    fh.write('%s\n' % edit)
                fh.write('\n')


class Dialog(QtGui.QDialog):
    
    def __init__(self):
        super(Dialog, self).__init__()
        self._setup_ui()
    
    def _setup_ui(self):
        
        self.setWindowTitle("Reference Edit Export")
        self.setLayout(QtGui.QVBoxLayout())
        self.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Fixed)
        
        group = QtGui.QGroupBox('References')
        self.layout().addWidget(group)
        group.setLayout(QtGui.QVBoxLayout())
        
        self._refs = []
        for ref_path in cmds.file(q=True, reference=True):
            ref_name = cmds.file(ref_path, q=True, namespace=True)
            checkbox = QtGui.QCheckBox(ref_name)
            checkbox.setChecked(True)
            group.layout().addWidget(checkbox)
            self._refs.append((ref_name, ref_path, checkbox))
        
        self._exporter = RefEditExporter()
        self._exporter_widget = sgpublish.exporter.ui.tabwidget.Widget()
        self.layout().addWidget(self._exporter_widget)
        
        # Work area.
        tab = sgpublish.exporter.ui.workarea.Widget(self._exporter, {
            'directory': 'data/refedits',
            'sub_directory': '',
            'extension': '.mel',
            'warning': self._warning,
            'error': self._warning,
        })
        self._exporter_widget.addTab(tab, "Export to Work Area")
        
        # SGPublishes.
        tab = sgpublish.exporter.ui.publish.maya.Widget(self._exporter)
        tab.beforeScreenshot.connect(lambda *args: self.hide())
        tab.afterScreenshot.connect(lambda *args: self.show())
        self._exporter_widget.addTab(tab, "Publish to Shotgun")
        
        button_row = QtGui.QHBoxLayout()
        button_row.addStretch()
        self.layout().addLayout(button_row)
        
        self._button = button = QtGui.QPushButton("Export")
        button.clicked.connect(self._on_export)
        button_row.addWidget(button)
        
    def _on_export(self, *args):
        references = [path for name, path, checkbox in self._refs if checkbox.isChecked()]
        publisher = self._exporter_widget.export(references=references)
        if publisher:
            sgpublish.uiutils.announce_publish_success(publisher)
        self.close()
        
    def _warning(self, message):
        cmds.warning(message)

    def _error(self, message):
        cmds.confirmDialog(title='Scene Name Error', message=message, icon='critical')
        cmds.error(message)


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
