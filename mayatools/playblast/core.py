from maya import cmds

from .. import context

__also_reload__ = [
    '..context',
]


settings = {
    'attrs': {
        'defaultRenderGlobals.imageFormat': 8, # JPEG.
        'defaultResolution.width': 1280,
        'defaultResolution.height': 720,
        'defaultResolution.deviceAspectRatio': 1280.0 / 720,
        'defaultResolution.pixelAspect': 1.0,
        'defaultResolution.dotsPerInch': 72,
        'defaultResolution.pixelDensityUnits': 0,
    },
    'camera_attrs': {
        'horizontalFilmOffset': 0,
        'verticalFilmOffset': 0,
    },
    'camera': {
        'displayFilmGate': 0,
        'displayResolution': 1,
        'overscan': 1,
    },
}


def playblast(**kwargs):

    # Extract the camera from the active view.
    try:
        editor = cmds.playblast(activeEditor=True)
        camera = cmds.modelEditor(editor, query=True, camera=True)
    except RuntimeError:
        camera_attrs = {}
        cmds.warning('Could not get camera for playblast')
    else:
        camera_attrs = dict((camera + '.' + k, v) for k, v in settings['camera_attrs'].iteritems())
    
    # So much state! Can we have Python2.7 now?
    with context.attrs(settings['attrs'], camera_attrs):
        with context.command(cmds.camera, camera, edit=True, **settings['camera']):
            with context.command(cmds.currentUnit, linear='cm', time='film'):
                return cmds.playblast(**kwargs)

