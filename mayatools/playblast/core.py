from __future__ import division

import tempfile

from maya import cmds

from .. import context


defaults = {
    'global_attrs': {
        # 'defaultResolution.deviceAspectRatio': 1280.0 / 720,
        # 'defaultResolution.dotsPerInch': 72,
        # 'defaultResolution.pixelAspect': 1.0,
        # 'defaultResolution.pixelDensityUnits': 0,
        'defaultRenderGlobals.imageFormat': 8, # JPEG.
        # 'hardwareRenderingGlobals.motionBlurEnable': True,
        'hardwareRenderingGlobals.motionBlurSampleCount': 32,
        'hardwareRenderingGlobals.multiSampleEnable': True,
        'hardwareRenderingGlobals.ssaoEnable': True,
        'hardwareRenderingGlobals.ssaoSamples': 16,
    },
    'camera_edit': {
        'displayFilmGate': 1,
        'displayGateMask': 1,
        'displayGateMaskOpacity': 0.85,
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
    
    # Make sure they are divisible by 2.
    width  += width % 2
    height += height % 2

    kwargs['widthHeight'] = (width, height)
    kwargs.setdefault('offScreen', True)
    kwargs.setdefault('forceOverwrite', True)
    kwargs.setdefault('percent', 100)
    
    global_attrs = dict(kwargs.pop('global_attrs', {}))
    for k ,v in defaults['global_attrs'].items():
        global_attrs.setdefault(k, v)

    camera_edit = dict(kwargs.pop('camera_edit', {}))
    for k, v in defaults['camera_edit'].items():
        camera_edit.setdefault(k, v)

    with context.attrs(global_attrs):
        with context.command(cmds.camera, camera, edit=True, **(camera_edit if camera else {})):
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

