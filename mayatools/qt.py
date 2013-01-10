import sip

from uitools.qt import QtCore

import maya.OpenMayaUI as apiUI


def get_maya_window():
    """
    Get the main Maya window as a QtGui.QMainWindow instance
    @return: QtGui.QMainWindow instance of the top level Maya windows
    """
    ptr = apiUI.MQtUtil.mainWindow()
    if ptr is not None:
        return sip.wrapinstance(long(ptr), QtCore.QObject)


def maya_to_qt(maya_object):
    """
    Convert a Maya ui path to a Qt object
    @param maya_object: Maya UI Path to convert (Ex: "scriptEditorPanel1Window|TearOffPane|scriptEditorPanel1|testButton" )
    @return: PyQt representation of that object
    """
    ptr = (
        apiUI.MQtUtil.findControl(maya_object) or
        apiUI.MQtUtil.findLayout(maya_object) or
        apiUI.MQtUtil.findMenuItem(maya_object)
    )
    if ptr is not None:
        return sip.wrapinstance(long(ptr), QtCore.QObject)