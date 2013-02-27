import errno
import os
import re
from shutil import copy, move, rmtree
from optparse import OptionParser

from maya import cmds

import qbfutures.maya

from .. import context


def selected_fluid_caches():
    return find_related_fluid_caches(cmds.ls(sl=True) or ())


def find_related_fluid_caches(nodes):

    nodes = list(nodes)

    visited = set()
    cache_map = dict()
    while nodes:
        
        node = nodes.pop(0)
        if node in visited:
            continue
        visited.add(node)
        
        type_ = cmds.nodeType(node)
        
        if type_ == 'transform':
            nodes.extend(cmds.listRelatives(node, path=True, children=True) or ())
            continue
        
        if type_ == 'fluidShape':
            caches = list(set(cmds.listConnections(node, type='cacheFile') or ()))
            if caches:
                cache_map[node] = caches[0]
            continue
        
    return cache_map


def interpolate_on_farm(fluid_node, cache_node, start, end, rate, chunk=10, debug=False):

    src_dir = cmds.getAttr(cache_node + '.cachePath')
    base_name = cmds.getAttr(cache_node + '.cacheName')

    if rate > 1:
        rate_str = ('%.3f' % rate).rstrip('0').rstrip('.')
    else:
        rate_str = ('x%.3f' % (1.0 / rate)).rstrip('0').rstrip('.')
    dst_dir = src_dir + '_' + rate_str

    try:
        os.makedirs(dst_dir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    executor = qbfutures.maya.Executor(clone_environ=True, create_tempfile=True, cpus=4)
    with executor.batch('Interpolate Fluid') as batch:

        if not debug:
            batch.submit('%s:_fix_xml', dst_dir, src_dir, base_name)
        else:
            _fix_xml(dst_dir, src_dir, base_name)

        for chunk_start in xrange(start, end, chunk):
            chunk_end = min(end, chunk_start + chunk)
            if not debug:
                batch.submit('%s:_interpolate' % __name__, dst_dir, fluid_node, cache_node, chunk_start, chunk_end, rate)
            else:
                _interpolate(dst_dir, fluid_node, cache_node, chunk_start, chunk_end, rate)

    return batch.futures


def _fix_xml(dst_dir, src_dir, base_name):

    with open(os.path.join(src_dir, base_name + '.xml')) as fh:
        xml = fh.read()

    xml = xml.replace('SamplingType="Regular"', 'SamplingType="Irregular"')

    with open(os.path.join(dst_dir, base_name + '.xml'), 'w') as fh:
        fh.write(xml)


def _interpolate(dst_dir, fluid_node, cache_node, start, end, rate):

    src_dir = cmds.getAttr(cache_node + '.cachePath')
    base_name = cmds.getAttr(cache_node + '.cacheName')

    tmp_dir = dst_dir + '_%04d_to_%04d' % (start, end)
    try:
        os.makedirs(tmp_dir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    # Copy over the XML.
    src_xml_path = os.path.join(src_dir, '%s.xml' % base_name)
    tmp_xml_path = os.path.join(tmp_dir, '%s.xml' % base_name)
    copy(src_xml_path, tmp_xml_path)

    # Copy over all of the frames that we are using.
    print 'Copying cache to tmp working area...'
    frame_re = re.compile(r'^%sFrame(\d+)\.mc$' % re.escape(base_name))
    found_frame_nos = set()
    for file_name in os.listdir(src_dir):
        m = frame_re.match(file_name)
        if m:
            frame_no = int(m.group(1))
            if frame_no >= start and frame_no <= end:
                found_frame_nos.add(frame_no)
                print '\t' + file_name
                copy(os.path.join(src_dir, file_name), tmp_dir)
    print 'Done.'

    missing_frame_nos = set(xrange(start, end + 1)).difference(found_frame_nos)
    if missing_frame_nos:
        print 'Missing frames: ', ', ',join(str(x) for x in sorted(missing_frame_nos))
        exit(3)

    print 'Interpolating...'
    with context.attrs({cache_node + '.cachePath': tmp_dir}):

        cmds.cacheFile(
            cacheFileNode=cache_node,
            cacheableNode=fluid_node,
            # refresh=True,
            replaceCachedFrame=True,
            runupFrames=0,
            #interpStartTime=opts.start,
            #interpEndTime=opts.end,
            inTangent='linear',
            outTangent='linear',
            startTime=start,
            endTime=end,
            simulationRate=rate,
            sampleMultiplier=1,
            # fileName='interp',
            # prefix=True,
            # directory='interp', # Does not do anything.
            noBackup=True,
        )

    print 'Done.'

    print 'Moving frames into place...'
    for file_name in os.listdir(tmp_dir):
        if os.path.splitext(file_name)[1] == '.mc':
            print '\t' + file_name
            try:
                os.unlink(os.path.join(dst_dir, file_name))
            except OSError as e:
                if e.errno != errno.ENOENT:
                    raise
            move(os.path.join(tmp_dir, file_name), dst_dir)
    print 'Done.'

    print 'Cleaning up...'
    rmtree(tmp_dir, ignore_errors=True)
    print 'Done.'










if __name__ == '__main__':
    main()
