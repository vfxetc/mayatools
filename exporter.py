from __future__ import absolute_import

from PyQt4 import QtCore, QtGui
Qt = QtCore.Qt

from maya import cmds

from ks.core.scene_name.widget import SceneNameWidget



def __before_reload__():
    if dialog:
        dialog.close()

dialog = None

def run():
    
    global dialog
    
    if dialog:
        dialog.close()
    
    dialog = QtGui.QDialog()
    layout = QtGui.QVBoxLayout()
    dialog.setLayout(layout)
    
    sets_box = QtGui.QGroupBox("Geometry to Cache")
    sets_box.setLayout(QtGui.QVBoxLayout())
    layout.addWidget(sets_box)
    for set in cmds.ls(sets=True):
        if set.startswith('cache_'):
            sets_box.layout().addWidget(QtGui.QLabel(set))
    if not sets_box.layout().count():
        sets_box.layout().addWidget(QtGui.QLabel("Nothing to cache."), alignment=Qt.AlignHCenter)
    
    scene_name_box = QtGui.QGroupBox("Geo Cache Name")
    scene_name_box.setLayout(QtGui.QVBoxLayout())
    layout.addWidget(scene_name_box)
    
    scene_name = SceneNameWidget(dict(
        scenes_name='data/geoCache',
        sub_directory='',
        workspace=cmds.workspace(q=True, rd=True),
    ))
    scene_name_box.layout().addWidget(scene_name)
    
    button_layout = QtGui.QHBoxLayout()
    layout.addLayout(button_layout)
    
    local_button = QtGui.QPushButton("Process Locally")
    button_layout.addWidget(local_button)
    qube_button = QtGui.QPushButton("Process on Farm")
    button_layout.addWidget(qube_button)
    
    dialog.show()
