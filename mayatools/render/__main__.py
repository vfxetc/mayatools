import os

from .command import main as main


try:
    code = main() or 0
except SystemExit as e:
    os._exit(e.args[0])
except:
    os._exit(1)
else:
    os._exit(code)
