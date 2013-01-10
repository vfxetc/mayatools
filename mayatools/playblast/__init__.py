try:
    from maya import cmds
    assert cmds # Silence pyflakes.
except ImportError:
    def playblast(*args, **kwargs):
        raise RuntimeError('not in maya')
else:
    from .core import playblast
    assert playblast # Silence pyflakes.
