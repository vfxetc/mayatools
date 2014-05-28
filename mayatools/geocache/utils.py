import os
import re

from maya import cmds, mel

from mayatools import mcc


def get_cache_channels(cache_path):
    if cache_path is None:
        return []
    try:
        return mcc.get_channels(cache_path)
    except mcc.ParseError as e:
        cmds.warning('Could not parse MCC for channel data; %r' % e)
        channels = cmds.cacheFile(q=True, fileName=cache_path, channelName=True)
        return [(c, None) for c in channels]


def get_point_counts(meshes):
    return [(mesh, cmds.getAttr(mesh + '.vrts', size=True)) for mesh in meshes]

    
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
        cache_path = cmds.cacheFile(cache_node, q=True, fileName=True)[0]
            
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
                
        shapes = cmds.listRelatives(transform, children=True, shapes=True) or []
        
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
        if len(shapes) != 1:
            cmds.warning('Could not identify shape connected to %r; found %r' % (cache_node, shapes))
            yield cache_node, cache_path, channel, transform, None
            continue
        shape = shapes[0]
        
        
        yield cache_node, cache_path, channel, transform, shape
    

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


def export_cache(members, path, name, frame_from, frame_to, world, as_abc=False):

    if not os.path.exists(path):
        os.makedirs(path)
    
    # See maya_base/scripts/other/doCreateGeometryCache.mel
    maya_version = int(cmds.about(version=True).split()[0])
    version = 6 if maya_version >= 2013 else 4
    
    args = [
        0, # 0 -> Use provided start/end frame.
        frame_from,
        frame_to,
        "OneFilePerFrame", # File distribution mode.
        0, # Refresh during caching?
        path, # Directory for cache files.
        0, # Create cache per geometry?
        name, # Name of cache file.
        0, # Is that name a prefix?
        "export", # Action to perform.
        1, # Force overwrites?
        1, # Simulation rate.
        1, # Sample multiplier.
        0, # Inherit modifications from cache to be replaced?
        1, # Save as floats.
    ]
    
    if version >= 6:
        args.extend((
            "mcc", # Cache format.
            int(world), # Save in world space?
        ))
    
        
    cmds.refresh(suspend=True)
    original_selection = cmds.ls(selection=True)
    hidden_layers = [layer for layer in cmds.ls(type="displayLayer") or () if not cmds.getAttr(layer + '.visibility')]
    
    try:
        
        for layer in hidden_layers:
            cmds.setAttr(layer + '.visibility', True)
        
        cmds.select(members, replace=True)
        
        mel.eval('doCreateGeometryCache %s { %s }' % (
            version,
            ', '.join('"%s"' % x for x in args),
        ))

        if as_abc:
            job = '''
                -sl
                -frameRange {frame_from} {frame_to}
                -file {path}.abc
            '''
            print 'AbcExport job:', job
            cmds.AbcExport(j=re.sub(r'\s+', ' ', job).format(**locals()))
    
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
    