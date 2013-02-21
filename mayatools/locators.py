import re

from maya import cmds

from . import context
from .transforms import transfer_global_transforms


def bake_global_locators(nodes):
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

    locator_to_transform = {}

    for transform in transforms:
        name = re.sub(r'\W+', '_', transform).strip('_') + '_locator'
        locator = cmds.spaceLocator(name=name)[0]
        locator_to_transform[locator] = transform

    transfer_global_transforms(locator_to_transform)

    return sorted(locator_to_transform)


def iter_nuke_script(locator, time_range=None):

    if time_range is None:
        time_range = (cmds.playbackOptions(q=True, minTime=True), cmds.playbackOptions(q=True, maxTime=True))
    min_time, max_time = time_range

    yield 'Axis2 {\n'
    yield '\tname %s\n' % re.sub(r'\W+', '_', locator).strip('_')

    # Note that this should always be XYZ, even if the original locator was set
    # to something else, since the baking process transfers all transformations
    # onto a new locator which defaults to XYZ.
    yield '\trot_order %s\n' % ('XYZ', 'YZX', 'ZXY', 'XZY', 'YXZ', 'ZYX')[cmds.getAttr('%s.rotateOrder' % locator)]

    for name, key in (('translate', 't'), ('rotate', 'r'), ('scaling', 's')):
        yield '\t%s {\n' % name
        for axis in 'xyz':
            yield '\t\t{curve x%d' % min_time
            for time in xrange(min_time, max_time + 1):
                yield ' %f' % cmds.getAttr('%s.%s%s' % (locator, key, axis), time=time)
            yield '}\n'
        yield '\t}\n'
    yield '}\n'


