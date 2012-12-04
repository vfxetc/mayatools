from __future__ import absolute_import

import functools
import os
import platform
import subprocess
import sys
import tempfile
import time
import traceback

from PyQt4 import QtCore, QtGui
Qt = QtCore.Qt

from maya import cmds, mel
import maya.utils

import sgactions.ticketui
import shotgun_api3_registry


__also_reload__ = [
    'sgactions.ticketui',
]



_registered = False
def register_hook():
    _registered = True
    maya.utils._guiExceptHook = _exception_hook


# Somewhere to store our state.
exceptions = []


def _exception_hook(exc_type, exc_value, exc_traceback, detail=2):
    exceptions.append((exc_type, exc_value, exc_traceback))
    try:
        return maya.utils.formatGuiException(exc_type, exc_value, exc_traceback, detail)
    except:
        return '# '.join(traceback.format_exception(tb_type, exc_object, tb)).rstrip()


class Dialog(sgactions.ticketui.Dialog):

    def _get_reply_data(self, exc_info):

        data = [
            ('User Comment', str(self._description.toPlainText())),
            ('Maya Context', {
                'file': cmds.file(q=True, expandName=True),
                'workspace': cmds.workspace(q=True, rootDirectory=True),
                'version': int(mel.eval('about -version').split()[0]),
            }),
            ('Maya Selection', cmds.ls(sl=True)),
            ('Maya References', cmds.file(q=True, reference=True)),
        ]
        if exc_info:
            data.append(('Traceback', exc_info))
        data.append(('OS Environment', dict(os.environ)))
        return data


# Our own brand of the ticket UI.
ticket_ui_context = functools.partial(sgactions.ticketui.ticket_ui_context, dialog_class=Dialog)


# Cleanup the submit dialog on autoreload.
dialog = None
def __before_reload__():
    global dialog
    if dialog:
        dialog.close()
        dialog.destroy()
    return _registered, exceptions

def __after_reload__(state=None):
    if state:
        registered, old_exceptions = state
        if registered:
            register_hook()
        exceptions.extend(old_exceptions)


def run_submit_ticket():
    global dialog
    if dialog:
        dialog.close()
    dialog = Dialog(exceptions=exceptions)
    dialog.show()
        