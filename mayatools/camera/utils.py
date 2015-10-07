from maya import cmds


def get_renderable_cameras(shapes=False):

    # ... but this will grab transforms.
    cameras = cmds.listCameras(perspective=True) or ()

    # Leave out the default camera.
    cameras = [c for c in cameras if c.split('|')[-1] != 'persp']

    # Leave out non-renderable ones.
    cameras = [c for c in cameras if cmds.getAttr(c + '.renderable')]

    if shapes:
        shapes = []
        for c in cameras:
            shapes.extend(cmds.listRelatives(c, children=True, type='camera') or [])
        return shapes

    return cameras

