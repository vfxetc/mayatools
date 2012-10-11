import re

from maya import cmds, mel


def simple_name(input_name):
    """Get a simpler name for comparisons.
    
    We remove some common words, trailing numbers, namespaces, paths, and
    collapse all non-alphanumerics into underscores.
    
    """
    name = input_name.lower()
    name = re.sub(r'[^:|]*[:|]', '', name)
    name = re.sub(r'(deformed|orig(inal)?s?|geo(metry)?|shapes?|spl?ines?)', '_', name)
    name = re.sub(r'[\d_]+$', '', name)
    name = re.sub(r'[^a-z0-9]', '_', name)
    name = name.strip('_')
    return name


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
    
    """

    cache_nodes = cmds.ls(type='cacheFile') or []
    for cache_node in cache_nodes:
        cache_path = cmds.cacheFile(cache_node, q=True, fileName=True)[0]
            
        ## Identify what it is connected to.
            
        channel = cmds.getAttr(cache_node + '.channel[0]')
            
        switch = cmds.listConnections(cache_node + '.outCacheData[0]')
        if not switch:
            cmds.warning('cacheFile %r is not connected' % cache_node)
            continue
        switch = switch[0]
        switch_type = cmds.nodeType(switch)
        
        # Pass through blends.
        if switch_type == 'cacheBlend':
            blend = switch
            switch = cmds.listConnections(blend + '.outCacheData[0]')
            if not switch:
                cmds.warning('cacheBlend %r is not connected' % blend)
                continue
            switch = switch[0]
            switch_type = cmds.nodeType(switch)
            
        if switch_type != 'historySwitch':
            cmds.warning('Unknown cache node layout; found %s %r' % (switch_type, switch))
            continue
        
        # The switch hooks onto a transform, but we want the shapes.
        transform = cmds.listConnections(switch + '.outputGeometry[0]')[0]
        shapes = cmds.listRelatives(transform, children=True, shapes=True)
        
        # Maya will often add a "Deformed" copy of a mesh
        if (len(shapes) == 2 and
            shapes[1][:len(shapes[0])] == shapes[0] and
            shapes[1][len(shapes[0]):] == 'Deformed'
        ):
            shapes = [shapes[0]]
        if len(shapes) != 1:
            cmds.warning('Could not identify single shape connected to cache; found %r' % shapes)
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
        mapping = mappings.setdefault(cache_path, {})
        mapping[shape] = channel
    return mappings
