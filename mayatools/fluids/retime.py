import math
from optparse import OptionParser

from .core import Cache


def frange(a, b, step):
    v = float(a)
    b = float(b)
    step = float(step)
    while v <= b:
        yield v
        v += step

def main():

    option_parser = OptionParser(usage='%prog [options] /path/to/cache.xml')
    option_parser.add_option('-s', '--start', type='float')
    option_parser.add_option('-e', '--end', type='float')
    option_parser.add_option('-r', '--rate', type='float', default=1.0)
    opts, args = option_parser.parse_args()

    if len(args) != 1:
        option_parser.print_usage()
        exit(1)

    cache = Cache(args[0])
    cache.pprint()

    # Load the headers for all the frames, and sort them by time.
    cache.frames.sort(key=lambda f: f.start_time)
    if not cache.frames:
        print 'No frames in cache.'
        exit(2)

    if opts.start is None:
        start_time = cache.frames[0].start_time
    else:
        start_time = int(opts.start * cache.time_per_frame)

    if opts.end is None:
        end_time = cache.frames[-1].end_time
    else:
        end_time = int(opts.end * cache.time_per_frame)

    # This one remains a float.
    rate = opts.rate * cache.time_per_frame

    frames = [f for f in cache.frames if f.start_time >= start_time and f.end_time <= end_time]
    rate_str = ('%.3f' % rate).rstrip('0').rstrip('.')
    print '%d frames from %d to %d, evaluating every %s ticks' % (len(frames), start_time, end_time, rate_str)

    # Iterate over the requested ticks.
    for tick in frange(start_time, end_time, rate):
        tick = int(round(tick))

        frame_a = [f for f in frames if f.start_time <= tick][-1]
        frame_b = next(f for f in frames if f.start_time >= tick)
        if frame_a is frame_b:
            new_frame = frame_a
            print 'use %d' % frame_a.start_time
            frame_a.pprint()
        else:
            print 'interpolate %d from %d and %d' % (tick, frame_a.start_time, frame_b.start_time)
            frame_a.pprint()
            frame_b.pprint()
        print '---'


if __name__ == '__main__':
    main()
