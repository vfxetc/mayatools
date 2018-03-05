from __future__ import division

import tempfile

from maya import cmds

from .. import context


settings = {
    'global_attrs': {
        'defaultRenderGlobals.imageFormat': 8, # JPEG.
        # 'defaultResolution.deviceAspectRatio': 1280.0 / 720,
        # 'defaultResolution.pixelAspect': 1.0,
        # 'defaultResolution.dotsPerInch': 72,
        # 'defaultResolution.pixelDensityUnits': 0,
    },
    'camera': {
        'displayFilmGate': 0,
        'displayResolution': 1,
        'overscan': 1,
    },
}


def playblast(**kwargs):

    # Extract the camera from the active view.
    panel = cmds.playblast(activeEditor=True)
    panel_type = cmds.getPanel(typeOf=panel) 
    if panel_type == 'modelPanel':
        camera = cmds.modelPanel(panel, query=True, camera=True)
    else:
        cmds.warning('%s is not a modelling panel; playblasts will not correctly setup the camera' % panel)
        camera = None
    
    width = cmds.getAttr('defaultResolution.width')
    height = cmds.getAttr('defaultResolution.height')

    # Get requested resolution from kwargs. Need to do this in two stages.
    max_width = kwargs.pop('width', 1024)
    max_height = kwargs.pop('height', 540)
    max_width, max_height = kwargs.pop('widthHeight', (max_width, max_height))

    width_ratio = width / max_width
    height_ratio = height / max_height
    if width_ratio > 1 or height_ratio > 1:
        if width_ratio > height_ratio:
            height = max_width * height // width
            width = max_width
        else:
            width = max_height * width // height
            height = max_height
                
    kwargs['widthHeight'] = (width, height)
    kwargs.setdefault('offScreen', True)
    kwargs.setdefault('forceOverwrite', True)
    kwargs.setdefault('percent', 100)
    
    with context.attrs(settings['global_attrs']):
        with context.command(cmds.camera, camera, edit=True, **(settings['camera'] if camera else {})):
            return cmds.playblast(**kwargs)


def screenshot(frame=None, **kwargs):
    path = tempfile.NamedTemporaryFile(suffix=".jpg", prefix="screenshot.", delete=False).name
    frame = cmds.currentTime(q=True) if frame is None else frame
    playblast(
        frame=[frame],
        format='image',
        completeFilename=path,
        viewer=False,
        p=100,
        framePadding=4, # ??
    )
    return path

