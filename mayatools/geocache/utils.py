import os
import re

from maya import cmds, mel

import abctools.maya.export

from mayatools import mcc
from mayatools.sets import reduce_sets
from mayatools.camera.utils import get_renderable_cameras


def get_cache_channels(cache_path):
    if cache_path is None:
        return []
    try:
        return mcc.get_channels(cache_path)
    except mcc.ParseError as e:
        raise
        cmds.warning('Could not parse MCC for channel data; %r' % e)
        channels = cmds.cacheFile(q=True, fileName=cache_path, channelName=True)
        return [(c, None) for c in channels]


def get_point_counts(meshes):
    return [(mesh, get_point_count(mesh)) for mesh in meshes]

def get_point_count(mesh):
    if cmds.nodeType(mesh) in ['mesh']:
        return get_poly_point_count(mesh)
    elif cmds.nodeType(mesh) in ['nurbsSurface']:
        return get_nurbs_surface_point_count(mesh)

def get_poly_point_count(mesh):
    return cmds.getAttr(mesh + '.vrts', size=True)

def get_nurbs_surface_point_count(mesh):
    return len(cmds.ls('%s.cv[*]'% mesh, flatten=True))

    
def basename(name):
    return re.sub(r'[^:|]*[:|]', '', name)


def simple_name(input_name):
    """Get a simpler name for comparisons.
    
    We remove some common words, trailing numbers, namespaces, paths, and
    collapse all non-alphanumerics into underscores.
    
    """
    name = input_name.lower()
    name = basename(name)
    name = re.sub(r'(deformed|orig(inal)?s?|geo(metry)?|shapes?|spl?ines?)', '_', name)
    name = re.sub(r'[\d_]+$', '', name)
    name = re.sub(r'[^a-z0-9]', '_', name)
    name = name.strip('_')
    return name


def get_reference_namespace(reference):
    try:
        namespace = cmds.referenceQuery(reference, namespace=True, xxx=True)
    except RuntimeError:
        return
    except TypeError:
        nodes = cmds.referenceQuery(reference, nodes=True)
        if nodes:
            name = nodes[0]
            name = name.split('|', 1)[0]
            namespace = name.rsplit(':', 1)[0]
        else:
            namespace = None
    if namespace:
        return namespace.strip(':')
        
    
def get_transform(input_node):
    """Walk the heirarchy looking for the nearest parent which is a transform."""
    node = input_node
    while True:
        type_ = cmds.nodeType(node)
        if type_ == 'transform':
            return node
        relatives = cmds.listRelatives(node, parent=True)
        if not relatives:
            return None
        node = relatives[0]


def delete_cache(node):
    print '# Deleting cache:', node
    mel.eval('deleteCacheFile(3, {"keep", "%s", "geometry"})' % node)


def iter_existing_cache_connections():
    """Yield data about every existing cache connection in the scene.
    
    :returns: Iterator of ``(cacheFile, fileName, channel, transform, shape)``
        tuples for each cache connection.
    
    It is possible for ``transform`` or ``shape`` to be ``None`` when the
    connection cannot be fully resolved. In every case that the connection is
    not complete, ``shape`` will be ``None``.
    
    """

    cache_nodes = cmds.ls(type='cacheFile') or []
    for cache_node in cache_nodes:

        cache_paths = cmds.cacheFile(cache_node, q=True, fileName=True)
        if not cache_paths:
            dir_ = cmds.getAttr('%s.cachePath' % cache_node)
            name = cmds.getAttr('%s.cacheName' % cache_node)
            cmds.warning(('cacheNode %s does not exist: %s/%s' % (cache_node, dir_, name)).replace('//', '/'))
            continue
        cache_path = cache_paths[0]
            
        ## Identify what it is connected to.
            
        channel = cmds.getAttr(cache_node + '.channel[0]')
            
        switch = cmds.listConnections(cache_node + '.outCacheData[0]')
        if not switch:
            cmds.warning('cacheFile %r is not connected' % cache_node)
            yield cache_node, cache_path, channel, None, None
            continue
        switch = switch[0]
        switch_type = cmds.nodeType(switch)
        
        # Pass through blends.
        if switch_type == 'cacheBlend':
            blend = switch
            switch = cmds.listConnections(blend + '.outCacheData[0]')
            if not switch:
                cmds.warning('cacheBlend %r is not connected' % blend)
                yield cache_node, cache_path, channel, None, None
                continue
            switch = switch[0]
            switch_type = cmds.nodeType(switch)
            
        if switch_type != 'historySwitch':
            cmds.warning('Unknown cache node layout; expected historySwitch, found %s %r' % (switch_type, switch))
            yield cache_node, cache_path, channel, None, None
            continue
        
        # The switch hooks onto a transform, but we want the shapes.
        transform = (cmds.listConnections(switch + '.outputGeometry[0]') or (None, ))[0]
        if transform is None:
            cmds.warning('Unknown cache node layout; nothing connected to %r' % switch)
            yield cache_node, cache_path, channel, None, None
            continue
        
        # Pass through groupParts. The control flow is a little wacky here, be
        # careful.
        while transform is not None:
            transform_type = cmds.nodeType(transform)
            if transform_type == 'groupParts':
                transform = (cmds.listConnections(transform + '.outputGeometry') or (None, ))[0]
                continue
            break
        if transform is None:
            transform_type = 'None'
        if transform_type != 'transform':
            cmds.warning('Unknown cache node layout; expected transform, found %s %r' % (transform_type, transform))
            yield cache_node, cache_path, channel, None, None
            continue
                
        shapes = cmds.listRelatives(transform, children=True, shapes=True) or ()
        shapes = isolate_deformed_shape(shapes)

        if len(shapes) != 1:
            cmds.warning('Could not identify shape connected to %r; found %r' % (cache_node, shapes))
            yield cache_node, cache_path, channel, transform, None
            continue
        shape = shapes[0]
        
        
        yield cache_node, cache_path, channel, transform, shape
    

def isolate_deformed_shape(shapes):
    # Maya will often add a "Deformed" copy of a mesh. Sometimes there is
    # a "Orig". Sometimes there are both.
    if len(shapes) > 1:
        a = basename(shapes[0])
        for other in shapes[1:]:
            b = basename(other)
            if not (b[:len(a)] == a and
                b[len(a):] in ('Deformed', 'Orig')
            ):
                break
        else:
            shapes = [shapes[0]]
    return shapes


def get_existing_cache_mappings():
    """Inspect the scene and determine which channels map to what.
    
    :return: ``dict`` mapping cache XML files to ``dict`` mapping shapes to
        channel names. E.g.::
        
            {
                '/path/to/cache.xml': {
                    'pSphereShape1': 'sphere_data',
                    ...
                },
                ...
            }
    
    Note that the returned shape is the one that the cache is connected to,
    which is often a duplicate of the original. Also that multiple caches may
    map to the same shape via a cacheBlend.
    
    """
    
    mappings = {}
    for cache_node, cache_path, channel, transform, shape in iter_existing_cache_connections():
        if shape is None:
            continue
        mapping = mappings.setdefault(cache_path, {})
        mapping[shape] = channel
    return mappings


def export_cache(members, path, name, frame_from, frame_to, world, alembic_metadata=None):
    
    # NOTE: This may not be nessesary since we are only doing Alembic export now.
    # Perhaps it was needed for MCCs. That is generally true for a LOT of the below.
    cmds.refresh(suspend=True)
    original_selection = cmds.ls(selection=True)
    hidden_layers = [layer for layer in cmds.ls(type="displayLayer") or () if not cmds.getAttr(layer + '.visibility')]
    
    try:
        
        for layer in hidden_layers:
            cmds.setAttr(layer + '.visibility', True)
    
        if not cmds.pluginInfo('AbcExport', q=True, loaded=True):
            print 'Loading AbcExport plugin...'
            cmds.loadPlugin('AbcExport')

        # We need to grab the shapes from the transforms.
        shapes = []
        transforms = []
        for node in members:
            if cmds.nodeType(node) == 'transform':
                node_shapes = cmds.listRelatives(node, children=True, shapes=True) or ()
                node_shapes = isolate_deformed_shape(node_shapes)
                if len(node_shapes) != 1:
                    cmds.warning('Transform %s did not have one obvious shape: %r' % (node, node_shapes))
                shapes.extend(node_shapes)
            else:
                shapes.append(node)

        # Include the first renderable camera.
        cameras = get_renderable_cameras()
        if not cameras:
            cmds.warning('No renderable cameras to export.')
        else:
            shapes.append(cameras[0])
            if len(cameras) > 1:
                cmds.warning('%s renderable cameras; only exporting %r' % (len(cameras), cameras[0]))

        file_info = cmds.fileInfo(q=True)
        file_info = dict(zip(file_info[0::2], file_info[1::2]))
        metadata = (alembic_metadata or {}).copy()
        metadata.update(
            file_info=file_info,
            references=[str(x) for x in cmds.file(query=True, reference=True) or []],
            sets=reduce_sets(),
        )

        cmds.select(shapes, replace=True)

        dir_ = os.path.dirname(os.path.abspath(path))
        if not os.path.exists(dir_):
            os.makedirs(dir_)

        # It is kinda silly that the "path" is supposed to be given with no
        # extension, but that is historical (due to MCC being the primary
        # originally).
        abctools.maya.export.export(path + '.abc',
            selection=True,
            uvWrite=True,
            frameRange=(int(frame_from), int(frame_to)),
            worldSpace=bool(world),
            metadata=metadata,
        )
    
    finally:
            
        # Restore selection.
        if original_selection:
            cmds.select(original_selection, replace=True)
        else:
            cmds.select(clear=True)
            
        # Restore visiblity
        for layer in hidden_layers:
            cmds.setAttr(layer + '.visibility', False)
            
        # Restore refresh
        cmds.refresh(suspend=False)
    
