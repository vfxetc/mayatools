
try:
    from maya import cmds
except ImportError:
    def playblast(*args, **kwargs):
        raise RuntimeError('not in maya')
else:
    from .core import playblast


