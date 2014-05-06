
try:
    from uitools.sip import wrapinstance
    from uitools.qt import QtCore
    import maya.OpenMayaUI as apiUI

# These modules will not exist while building the docs.
except ImportError:
    import os
    if os.environ.get('SPHINX') != 'True':
        raise


def get_maya_window():
    """Get the main Maya window as a QtGui.QMainWindow."""
    ptr = apiUI.MQtUtil.mainWindow()
    if ptr is not None:
        return wrapinstance(long(ptr), QtCore.QObject)


def maya_to_qt(maya_object):
    """Convert a Maya UI path to a Qt object.

    :param str maya_object: The path of the Maya UI object to convert.
    :returns: QtCore.QObject or None

    """
    
    ptr = (
        apiUI.MQtUtil.findControl(maya_object) or
        apiUI.MQtUtil.findLayout(maya_object) or
        apiUI.MQtUtil.findMenuItem(maya_object)
    )
    if ptr is not None:
        return wrapinstance(long(ptr), QtCore.QObject)