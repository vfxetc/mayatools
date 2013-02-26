import errno
import os
import re
from shutil import copy
from optparse import OptionParser

from maya import cmds


def main():

    opt_parser = OptionParser()
    opt_parser.add_option('-s', '--start', type='int')
    opt_parser.add_option('-e', '--end', type='int')
    opt_parser.add_option('-r', '--rate', type='float')

    opts, args = opt_parser.parse_args()

    if len(args) != 1:
        opt_parser.print_usage()
        exit(1)
    if not opts.start or not opts.end or not opts.rate:
        opt_parser.print_usage()
        exit(1)

    src_xml_path = args[0]

    src_dir = os.path.dirname(src_xml_path)
    base_name, base_ext = os.path.splitext(os.path.basename(src_xml_path))
    if base_ext != '.xml':
        print 'Cache path does not appear to be XML; exiting.'
        exit(2)

    dst_dir = src_dir + '_interp'
    try:
        os.makedirs(dst_dir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    # Copy over the XML and create a backup for it.
    dst_xml_path = os.path.join(dst_dir, '%s.xml' % base_name)
    copy(src_xml_path, dst_xml_path)
    xml_backup_path = os.path.join(dst_dir, '%s.original.xml' % base_name)
    copy(src_xml_path, xml_backup_path)

    # Copy over all of the frames that we are using.
    frame_re = re.compile(r'^%sFrame(\d+)\.mc$' % re.escape(base_name))
    found_frame_nos = set()
    for file_name in os.listdir(src_dir):
        m = frame_re.match(file_name)
        if m:
            frame_no = int(m.group(1))
            if frame_no >= opts.start and frame_no <= opts.end:
                found_frame_nos.add(frame_no)
                print 'Copying', file_name
                copy(os.path.join(src_dir, file_name), dst_dir)
    missing_frame_nos = set(xrange(opts.start, opts.end + 1)).difference(found_frame_nos)
    if missing_frame_nos:
        print 'Missing frames: ', ', ',join(str(x) for x in sorted(missing_frame_nos))
        exit(3)

    print 'Initializing Maya...'
    import maya.standalone
    maya.standalone.initialize()
    print 'Done.'

    fluid_shape = cmds.createNode('fluidShape')
    cache_node = cmds.cacheFile(createCacheNode=True, fileName=base_name, directory=dst_dir)

    cmds.cacheFile(
        cacheFileNode=cache_node,
        # cacheableNode=fluid_shape,#'fluidShape1',
        # refresh=True,
        replaceCachedFrame=True,
        runupFrames=0,
        #interpStartTime=opts.start,
        #interpEndTime=opts.end,
        inTangent='linear',
        outTangent='linear',
        startTime=opts.start,
        endTime=opts.end,
        simulationRate=opts.rate,
        sampleMultiplier=1,
        # fileName='interp',
        # prefix=True,
        # directory='interp', # Does not do anything.
    )










if __name__ == '__main__':
    main()
