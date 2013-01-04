import re

from maya import cmds

from . import context


def bake_global_locators(nodes, time_range=None):
    """Create a locator for each transform node (given or above given)
    and bake in the global transformation of that node.

    :param list nodes: Maya nodes to build locators for.
    :returns list: A :node:`locator` for each unique transform.

    """

    # Get a set of all unique transforms either given or above given.
    transforms = set()
    visited = set()
    to_visit = set(cmds.ls(nodes, long=True))
    while to_visit:
        node = to_visit.pop()
        if node in visited:
            continue
        visited.add(node)
        if cmds.nodeType(node) == 'transform':
            transforms.add(node)
            continue
        to_visit.update(cmds.listRelatives(node, allParents=True, fullPath=True) or ())

    if not transforms:
        raise ValueError('could not find transforms from given nodes')

    locators = []
    constraints = []
    for t in transforms:

        name = re.sub(r'\W+', '_', t).strip('_') + '_locator'
        l = cmds.spaceLocator(name=name)[0]
        locators.append(l)

        c1 = cmds.parentConstraint(t, l)
        c2 = cmds.scaleConstraint(t, l)
        constraints.extend((c1, c2))

    if time_range is None:
        time_range = (cmds.playbackOptions(q=True, minTime=True), cmds.playbackOptions(q=True, maxTime=True))
    
    with context.suspend_refresh():
        cmds.bakeResults(*locators, **dict(
            simulation=False,
            time=time_range,
        ))

    cmds.delete(*constraints)

    return locators


