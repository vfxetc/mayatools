import os
import traceback

from .command import main as main


# We exit really agressively, because the mayapy shutdown is not clean.
try:
    code = main() or 0
except SystemExit as e:
    os._exit(e.code or 0)
except:
    traceback.print_exc()
    os._exit(1)
else:
    os._exit(code)
