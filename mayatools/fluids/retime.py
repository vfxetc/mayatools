import math
import os
from optparse import OptionParser

from .core import Cache, Frame, Shape, Channel


def frange(a, b, step):
    v = float(a)
    b = float(b)
    step = float(step)
    while v <= b:
        yield v
        v += step

def main():

    option_parser = OptionParser(usage='%prog [options] input.xml, output.xml')
    option_parser.add_option('-s', '--start', type='float')
    option_parser.add_option('-e', '--end', type='float')
    option_parser.add_option('--src-start', '--os', type='float')
    option_parser.add_option('--src-end', '--oe', type='float')
    option_parser.add_option('-r', '--rate', type='float', default=1.0)
    option_parser.add_option('-v', '--verbose', action='count', default=0)
    opts, args = option_parser.parse_args()

    if len(args) != 2:
        option_parser.print_usage()
        exit(1)

    dst_path = os.path.abspath(args[1])
    dst_base_name, dst_ext = os.path.splitext(dst_path)
    if dst_ext != '.xml':
        option_parser.print_usage()
        exit(2)
    dst_directory, dst_base_name = os.path.split(dst_base_name)
    if not os.path.exists(dst_directory):
        os.makedirs(dst_directory)

    src_cache = Cache(args[0])
    if opts.verbose >= 2:
        src_cache.pprint()


    # Load the headers for all the frames, and sort them by time.
    src_cache.frames.sort(key=lambda f: f.start_time)
    if not src_cache.frames:
        print 'No frames in src_cache.'
        exit(2)

    # Construct the new src_cache that our frames will go into.
    dst_cache = src_cache.clone()

    # Convert all time options into an integer of ticks.
    if opts.start is None:
        dst_start = dst_cache.frames[0].start_time
    else:
        dst_start = int(opts.start * dst_cache.time_per_frame)
    if opts.end is None:
        dst_end = dst_cache.frames[-1].end_time
    else:
        dst_end = int(opts.end * dst_cache.time_per_frame)

    if opts.src_start is None:
        src_start = dst_start
    else:
        src_start = int(opts.src_start * src_cache.time_per_frame)
    if opts.src_end is None:
        src_end = dst_end
    else:
        src_end = int(opts.src_end * src_cache.time_per_frame)

    # This one remains a float.
    sampling_rate = opts.rate * src_cache.time_per_frame

    # Isolate the frames requested via src-*.
    frames = [f for f in src_cache.frames if f.start_time >= dst_start and f.end_time <= dst_end]

    # Iterate over the requested ticks.
    for dst_time in frange(dst_start, dst_end, sampling_rate):
        src_time = src_start + (src_end - src_start) * (dst_time - dst_start) / (dst_end - dst_start)
        print '%d <- %d' % (dst_time, src_time)

        # Create a new blank frame.
        dst_frame = Frame(dst_cache)
        dst_frame.set_times(dst_time, dst_time)
        dst_cache._frames.append(dst_frame)

        # Grab the two frames to blend between.
        frame_a = [f for f in frames if f.start_time <= src_time][-1]
        frame_b = next(f for f in frames if f.start_time >= src_time)

        if frame_a is frame_b:

            if opts.verbose:
                print '\tuse %d' % frame_a.start_time
            if opts.verbose >= 2:
                    frame_a.pprint()

            # Just copy the data over. It shouldn't get mutated....
            dst_frame.shapes.update(frame_a.shapes)
            dst_frame.channels.update(frame_a.channels)

        else:

            blend_factor = float(src_time - frame_a.start_time) / float(frame_b.start_time - frame_a.start_time)

            if opts.verbose:
                print '\tinterpolate %.3f from %d to %d' % (blend_factor, frame_a.start_time, frame_b.start_time)
            if opts.verbose >= 2:
                frame_a.pprint()
                frame_b.pprint()

            for shape_name, shape_a in sorted(frame_a.shapes.iteritems()):
                dst_shape = Shape.setup_blend(dst_frame, shape_name, frame_a, frame_b)
                dst_shape.blend(blend_factor)

        frame_no, tick = divmod(dst_time, dst_cache.time_per_frame)
        if tick:
            file_name = '%sFrame%dTick%d.mc' % (dst_base_name, frame_no, tick)
        else:
            file_name = '%sFrame%d.mc' % (dst_base_name, frame_no)
        file_name = os.path.join(dst_directory, file_name)
        if opts.verbose:
            print '\tsave to', file_name

        with open(file_name, 'wb') as fh:
            for chunk in dst_frame.dumps_iter():
                fh.write(chunk)

    # Write the new XML.
    dst_cache.update_xml()
    dst_cache.write_xml(dst_path)




if __name__ == '__main__':
    main()
