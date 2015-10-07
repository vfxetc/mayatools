from maya import cmds


def get_renderable_cameras():
    """Return all non-default renderable cameras.

    Returns the camera shape, not the transform.

    """

    cameras = cmds.ls(type='camera') or ()

    # Leave out orthographic cameras.
    cameras = [c for c in cameras if not cmds.getAttr(c + '.orthographic')]

    # Leave out the default perspective camera.
    cameras = [c for c in cameras if c.split('|')[-1] != 'perspShape']

    # Leave out non-renderable cameras.
    cameras = [c for c in cameras if cmds.getAttr(c + '.renderable')]

    return cameras
