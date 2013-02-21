import re

from maya import cmds

from . import context


def transfer_global_transforms(dst_to_src, time_range=None):
    """Bake global transform from one node onto another.

    :param dict dst_to_src: Mapping nodes to transfer transformations onto, to
        the nodes to source those transformations from.
    :param tuple time_range: ``(min_time, max_time)`` or None for the current
        playback timeframe.

    """

    dst_to_src = dict(dst_to_src)
    if not dst_to_src:
        return

    # Contrain every dst to their src.
    constraints = []
    for dst, src in dst_to_src.iteritems():
        constraints.extend((
            cmds.parentConstraint(src, dst),
            cmds.scaleConstraint(src, dst),
        ))

    if time_range is None:
        time_range = (cmds.playbackOptions(q=True, minTime=True), cmds.playbackOptions(q=True, maxTime=True))
    
    with context.suspend_refresh():
        cmds.bakeResults(*dst_to_src.iterkeys(), **dict(
            simulation=True,
            time=time_range,
        ))

    cmds.delete(*constraints)




