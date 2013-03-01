import ast
import os
import re
import xml.etree.cElementTree as etree

from .. import binary


class Cache(object):

    _interesting_extra = set((
        'dimensionsW', 'dimensionsH', 'dimensionsD',
        'resolutionW', 'resolutionH', 'resolutionD',
    ))

    def __init__(self, xml_path):

        self.xml_path = xml_path
        self.directory = os.path.dirname(self.xml_path)
        self.base_name = os.path.splitext(os.path.basename(self.xml_path))[0]

        self.parse_xml()

        self._frames = []

    def parse_xml(self):

        self.etree = etree.parse(self.xml_path)

        self.time_per_frame = int(self.etree.find('cacheTimePerFrame').get('TimePerFrame'))
        assert self.time_per_frame == 250, 'Non-standard TimePerFrame'

        self.cache_type = self.etree.find('cacheType').get('Type')
        assert self.cache_type == 'OneFilePerFrame', 'Not OneFilePerFrame'

        self.cache_format = self.etree.find('cacheType').get('Format')
        assert self.cache_format == 'mcc', 'Not "mcc"'

        # Parse all the extra info. We will extract resolution and dimensions
        # from this.
        self.extra = {}
        for element in self.etree.findall('extra'):
            m = re.match(r'^([^\.]+)\.(\w+)=(.+?)$', element.text)
            if not m:
                continue
            name, key, raw_value = m.groups()
            if key not in self._interesting_extra:
                continue
            try:
                value = ast.literal_eval(raw_value)
            except (ValueError, SyntaxError):
                value = raw_value
            self.extra.setdefault(name, {})[key] = value

        self.shape_specs = {}
        for name, data in sorted(self.extra.iteritems()):
            self.shape_specs[name] = ShapeSpec(name, **data)

        self.channel_specs = {}
        for channel_element in self.etree.find('Channels'):
            channel_spec = ChannelSpec.from_xml_attrib(channel_element.attrib)
            self.channel_specs[channel_spec.name] = channel_spec

    def pprint(self):
        print self.xml_path
        print '\ttimePerFrame:', self.time_per_frame
        print '\tcacheType:', self.cache_type
        print '\tcacheFormat:', self.cache_format
        print '\traw "extra" data:'
        for name, extra in sorted(self.extra.iteritems()):
            for k, v in sorted(extra.iteritems()):
                print '\t\t%s.%s: %r' % (name, k, v)
        print '\tshape specifications:'
        for name, shape_spec in sorted(self.shape_specs.iteritems()):
            print '\t\t%s:' % name
            print '\t\t\tdimensions:', shape_spec.dimensions
            print '\t\t\tresolution:', shape_spec.resolution
            print '\t\t\tunit_size:', shape_spec.unit_size
        print '\tchannel specifications:'
        for channel_name, channel_spec in sorted(self.channel_specs.iteritems()):
            print '\t\t%s' % (channel_name, )

    @property
    def frames(self):
        if not self._frames:

            name_re = re.compile(r'^%sFrame(\d+)(?:Tick(\d))?\.mc$' % re.escape(self.base_name))
            for file_name in os.listdir(self.directory):
                m = name_re.match(file_name)
                if m:
                    frame = Frame(self, os.path.join(self.directory, file_name))
                    self._frames.append(frame)

        return self._frames


class ShapeSpec(object):

    def __init__(self, name, **kwargs):
        self.name = name
        self.dimensions = tuple(kwargs.pop('dimensions' + axis) for axis in 'WHD')
        self.resolution = tuple(kwargs.pop('resolution' + axis) for axis in 'WHD')
        self.unit_size = tuple(float(d) / float(r) for d, r in zip(self.dimensions, self.resolution))

    def __repr__(self):
        return '<%s unit_size=%r>' % (self.__class__.__name__, self.unit_size)


class ChannelSpec(object):

    @classmethod
    def from_xml_attrib(cls, attrib):
        return cls(
            attrib['ChannelName'],
            attrib['ChannelInterpretation']
        )

    def __init__(self, name, interpretation=None):
        self.name = name
        self.shape, self.interpretation = self.name.rsplit('_', 1)
        if interpretation:
            assert self.interpretation == interpretation


class Frame(object):

    _header_tags = set(('STIM', 'ETIM', 'VRSN'))

    def __init__(self, cache=None, path=None):

        self.cache = cache
        self.path = path
        self.parser = None

        self._channels = {}
        self._headers = {}
        self._shapes = {}

    def pprint(self):
        print 'Frame from %d to %d' % (self.start_time, self.end_time)
        print 'Shapes:'
        for shape_name, shape in sorted(self.shapes.iteritems()):
            print '\t%s:' % shape_name
            print '\t\tresolution: %r' % (shape.resolution, )
            print '\t\toffset: %r' % (shape.offset, )
            print '\t\tbb_min: %r' % (shape.bb_min, )
            print '\t\tbb_max: %r' % (shape.bb_max, )

    def parse_headers(self):
        self.parser = self.parser or binary.Parser(open(self.path, 'rb'))
        while True:
            if all(tag in self._headers for tag in self._header_tags):
                break
            chunk = self.parser.parse_next()
            if chunk.tag in self._header_tags:
                self._headers[chunk.tag] = chunk.ints[0]

    @property
    def headers(self):
        if not self._headers and self.path:
            self.parse_headers()
        return self._headers

    @property
    def start_time(self):
        return self.headers.get('STIM')
    @property
    def end_time(self):
        return self.headers.get('ETIM')

    @property
    def channels(self):
        if not self._channels and self.path:
            self.parse_headers()
            self.parser.parse_all()
            channels = self.parser.find_one('MYCH')
            for name, data in zip(channels.find('CHNM'), channels.find('FBCA')):
                name = name.string
                data = data.floats
                self._channels[name] = Channel(self, name, data)
        return self._channels

    @property
    def shapes(self):
        if not self._shapes and self.channels:
            for shape_name, shape_spec in self.cache.shape_specs.iteritems():
                channels = dict((c.interpretation, c) for n, c in self.channels.iteritems() if c.spec.shape == shape_name)
                shape = Shape(self, shape_spec, channels)
                self._shapes[shape_name] = shape
        return self._shapes


class Shape(object):

    def __init__(self, frame, spec, channels):
        self.frame = frame
        self.cache = frame.cache
        self.spec = spec
        self.channels = channels

        res_channel = self.channels.get('resolution')
        if res_channel:
            self.resolution = res_channel.data
        else:
            self.resolution = self.spec.resolution

        off_channel = self.channels.get('offset')
        if off_channel:
            self.offset = off_channel.data
        else:
            self.offset = self.spec.offset

        self.bb_min = tuple(o - r * u / 2.0 for o, r, u in zip(self.offset, self.resolution, self.spec.unit_size))
        self.bb_max = tuple(o + r * u / 2.0 for o, r, u in zip(self.offset, self.resolution, self.spec.unit_size))


class Channel(object):

    def __init__(self, frame, name, data):
        self.frame = frame
        self.cache = frame.cache
        self.spec = self.cache.channel_specs[name]
        self.name = name
        self.interpretation = self.spec.interpretation
        self.data = data


if __name__ == '__main__':

    import sys
    cache = Cache(sys.argv[1])
    cache.pprint()

