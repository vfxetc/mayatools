import os
import re

from PyQt4 import QtCore, QtGui
Qt = QtCore.Qt

from maya import cmds, mel

from sgfs.ui import product_select
import sgfs.ui.scene_name.widget as scene_name
from sgpublish.importer.generic import Importer
from sgpublish.importer.ui.dialog import ImportDialog
from sgpublish.importer.ui.workarea import WorkAreaImporter
from sgpublish.importer.ui.publish import PublishImporter


class CameraImporter(Importer):

    def import_(self, path):
        try:
            ref_node = cmds.referenceQuery(path, referenceNode=True)
        except RuntimeError:
            pass
        else:
            cmds.warning('Already referenced')
            return
        cmds.file(path, reference=True)


class Dialog(ImportDialog):
    
    importer_class = CameraImporter

    def __init__(self, **kwargs):
        super(Dialog, self).__init__(**kwargs)
        
        workarea = WorkAreaImporter(self.importer)
        workarea.picker.register_section('Camera', self._iter_cameras)
        self.tabs.addTab(workarea, "From Work Area")

        publish = PublishImporter(self.importer, publish_type='maya_camera')
        self.tabs.addTab(publish, "From Publish")
    
    def _iter_cameras(self, step_path):
        if step_path is None:
            return
        camera_dir = os.path.join(step_path, 'maya', 'scenes', 'camera')
        if os.path.exists(camera_dir):
            for name in os.listdir(camera_dir):
                
                # Tempfiles.
                if name.startswith('.'):
                    continue

                # WesternX deals with ascii cameras.
                if not name.endswith('.ma'):
                    continue

                # Skip the versioned ones.
                if re.search(r'\.20\d{2}\.ma$', name):
                    continue
                
                m = re.search(r'v(\d+)(?:_r(\d+))?', name)
                if m:
                    priority = tuple(int(x or 0) for x in m.groups())
                else:
                    priority = (0, 0)

                cam_path = os.path.join(camera_dir, name)

                try:
                    ref_node = cmds.referenceQuery(cam_path, referenceNode=True)
                except RuntimeError:
                    pass
                else:
                    name += ' (already referenced)'
                    priority = (-1, 0) # Drop it to the bottom.
                
                yield name, cam_path, priority




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
