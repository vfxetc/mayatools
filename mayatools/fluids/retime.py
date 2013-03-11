import math
import os

from optparse import OptionParser

import qbfutures

from .core import Cache, Frame, Shape, Channel


def frange(a, b, step):
    v = float(a)
    b = float(b)
    step = float(step)
    while v <= b:
        yield v
        v += step


def iter_ticks(src_start, src_end, dst_start, dst_end, sampling_rate):
    for dst_time in frange(dst_start, dst_end, sampling_rate):
        src_time = src_start + (src_end - src_start) * (dst_time - dst_start) / (dst_end - dst_start)
        yield src_time, dst_time


def main():

    option_parser = OptionParser(usage='%prog [options] input.xml, output.xml')
    option_parser.add_option('-s', '--start', type='float')
    option_parser.add_option('-e', '--end', type='float')
    option_parser.add_option('--src-start', '--os', type='float')
    option_parser.add_option('--src-end', '--oe', type='float')
    option_parser.add_option('-r', '--rate', type='float', default=1.0)
    option_parser.add_option('-v', '--verbose', action='count', default=0)
    option_parser.add_option('-f', '--farm', action='store_true')
    option_parser.add_option('-w', '--workers', type='int', default=20)
    option_parser.add_option('-a', '--advect', action='store_true')
    opts, args = option_parser.parse_args()

    if len(args) != 2:
        option_parser.print_usage()
        exit(1)


    res = schedule_retime(*args,
        src_start=opts.src_start,
        src_end=opts.src_end,
        dst_start=opts.start,
        dst_end=opts.end,
        sampling_rate=opts.rate,
        verbose=opts.verbose,
        farm=opts.farm,
        workers=opts.workers,
        advect=opts.advect
    )

    if opts.farm:
        print 'Qube job ID', res


def schedule_retime(
    src_path, dst_path,
    src_start=None, src_end=None,
    dst_start=None, dst_end=None,
    sampling_rate=1.0,
    farm=True,
    workers=20,
    verbose=0,
    advect=True,
):

    dst_path = os.path.abspath(dst_path)
    src_path = os.path.abspath(src_path)

    dst_base_name, dst_ext = os.path.splitext(dst_path)
    if dst_ext != '.xml':
        option_parser.print_usage()
        exit(2)
    dst_directory, dst_base_name = os.path.split(dst_base_name)
    if not os.path.exists(dst_directory):
        os.makedirs(dst_directory)

    src_cache = Cache(src_path)
    if verbose >= 2:
        src_cache.pprint()


    # Load the headers for all the frames, and sort them by time.
    frame_times = []
    for frame in src_cache.frames:
        frame_times.append((frame.start_time, frame.path))
        frame.free()
    frame_times.sort()
    if not frame_times:
        print 'No frames in src_cache.'
        exit(2)

    # Reclaim the file handles.
    src_cache.free()

    # Construct the new src_cache that our frames will go into.
    dst_cache = src_cache.clone()
    dst_base_path = os.path.join(dst_directory, dst_base_name)

    # Convert all time options into an integer of ticks.
    if dst_start is None:
        dst_start = dst_cache.frames[0].start_time
    else:
        dst_start = int(dst_start * dst_cache.time_per_frame)
    if dst_end is None:
        dst_end = dst_cache.frames[-1].end_time
    else:
        dst_end = int(dst_end * dst_cache.time_per_frame)

    if src_start is None:
        src_start = dst_start
    else:
        src_start = int(src_start * src_cache.time_per_frame)
    if src_end is None:
        src_end = dst_end
    else:
        src_end = int(src_end * src_cache.time_per_frame)

    # This one remains a float.
    sampling_rate = sampling_rate * src_cache.time_per_frame

    # Isolate the frames requested via src-*.
    frames = [f for f in frame_times if f[0] >= dst_start and f[0] <= dst_end]

    # Write the new XML.
    dst_cache.update_xml(dst_start, dst_end)
    dst_cache.write_xml(dst_path)

    if farm:
        executor = qbfutures.Executor(cpus=workers, groups='farm', reservations='host.processors=1')
        with executor.batch(name='Retime Fluid:%s:%s' % (os.path.basename(src_cache.directory), src_cache.shape_specs.keys()[0])) as batch:

            for src_time, dst_time in iter_ticks(src_start, src_end, dst_start, dst_end, sampling_rate):
                frame_a_path = [f[1] for f in frame_times if f[0] <= src_time][-1]
                frame_b_path = next(f[1] for f in frame_times if f[0] >= src_time)
                batch.submit_ext(
                    func='mayatools.fluids.retime:blend_one_on_farm',
                    args=[src_cache.xml_path, src_time, dst_time, frame_a_path, frame_b_path, dst_base_path, advect],
                    name='Blend %d from %d' % (dst_time, src_time),
                )
        return batch.futures[0].job_id


    # Iterate over the requested ticks.
    for src_time, dst_time in iter_ticks(src_start, src_end, dst_start, dst_end, sampling_rate):
        frame_a_path = [f[1] for f in frame_times if f[0] <= src_time][-1]
        frame_b_path = next(f[1] for f in frame_times if f[0] >= src_time)
        blend_one_on_farm(src_cache.xml_path, src_time, dst_time, frame_a_path, frame_b_path, dst_base_path, advect)



def blend_one_on_farm(cache, src_time, dst_time, frame_a, frame_b, dst_base_path, advect):

    if isinstance(cache, basestring):
        cache = Cache(cache)
    if isinstance(frame_a, basestring):
        frame_a = Frame(cache, frame_a)
    if isinstance(frame_b, basestring):
        frame_b = Frame(cache, frame_b)

    dst_frame = Frame(cache)
    dst_frame.set_times(dst_time, dst_time)

    if frame_a.path == frame_b.path:
        dst_frame.shapes.update(frame_a.shapes)
        dst_frame.channels.update(frame_a.channels)

    else:
        blend_factor = float(src_time - frame_a.start_time) / float(frame_b.start_time - frame_a.start_time)
        for shape_name, shape_a in sorted(frame_a.shapes.iteritems()):
            dst_shape = Shape.setup_blend(dst_frame, shape_name, frame_a, frame_b)
            dst_shape.blend(blend_factor, advect)

    frame_no, tick = divmod(dst_time, cache.time_per_frame)
    if tick:
        dst_path = '%sFrame%dTick%d.mc' % (dst_base_path, frame_no, tick)
    else:
        dst_path = '%sFrame%d.mc' % (dst_base_path, frame_no)
    print 'Saving to', dst_path

    try:
        os.makedirs(os.path.dirname(dst_path))
    except OSError:
        pass

    with open(dst_path, 'wb') as fh:
        for chunk in dst_frame.dumps_iter():
            fh.write(chunk)



if __name__ == '__main__':
    main()
