import os
import sys
import traceback


print >> sys.__stderr__, '[mayatools.batchgui:client] Starting...'


try:
    from mayatools_batchgui import safe_call, setup
    safe_call(setup)
except:
    try:
        traceback.print_exc()
        os._exit(1)
    except:
        os._exit(2)
