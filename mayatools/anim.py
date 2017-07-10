import re

from maya import cmds


def has_keyframe_animated_xform(transform):
    """Determine if the given node has a keyframe animated transform.
    
    Having multiple keysframes with the same value and flat tangents counts
    as being *not* animated.

    .. warning:: Only checks for keyframes; constraints (or any other form of
        transformation) will not be detected!

    """

    connections = cmds.listConnections(transform, type='animCurve', connections=True) or ()
    for i in xrange(0, len(connections), 2):

        dst_plug = connections[i].split('.')[-1]
        src_node = connections[i + 1]

        if not re.match(r'^(translate|rotate(Order|Axis)?|scale|shear)[XYZ]*$', dst_plug):
            continue

        values = set(cmds.keyframe(src_node, q=True, valueChange=True) or ())
        if len(values) >= 2:
            return True

        tangents = cmds.keyTangent(src_node, q=True, iy=True, oy=True) or ()
        if any(tangents):
            return True

    return False

