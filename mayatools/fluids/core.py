import ast
import re
import xml.etree.cElementTree as etree

from .. import binary


class Cache(object):

    def __init__(self, xml_path):

        self.xml_path = xml_path

        self.parse_xml()

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
        self.attrs = {}
        for element in self.etree.findall('extra'):
            m = re.match(r'^([^\.]+)\.(\w+)=(.+?)$', element.text)
            if not m:
                continue
            name, key, raw_value = m.groups()
            try:
                value = ast.literal_eval(raw_value)
            except (ValueError, SyntaxError):
                value = raw_value
            self.attrs.setdefault(name, {})[key] = value

        self.channel_specs = {}
        for channel_element in self.etree.find('Channels'):
            channel = ChannelSpec.from_xml_attrib(channel_element.attrib)
            self.channel_specs[channel.name] = channel

    def pprint(self):
        print self.xml_path
        print '\ttime per frame:', self.time_per_frame
        print '\tcache type:', self.cache_type
        print '\tcache format:', self.cache_format
        print '\tattributes:'
        for name, attrs in sorted(self.attrs.iteritems()):
            print '\t\t%s:' % name
            for k, v in sorted(attrs.iteritems()):
                print '\t\t\t%s: %r' % (k, v)


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

    def __init__(self, path=None):

        self._channels = {}
        self.info = {}

        self.parser = None
        self.path = path
        if self.path:
            self.parse_headers()

    def parse_headers(self):
        with open(self.path) as fh:
            self.parser = binary.Parser(fh)
            while True:
                chunk = self.parser.parse_next()
                if chunk.tag in self._header_tags:
                    self.info[chunk.tag] = chunk.ints[0]
                if all(tag in self.info for tag in self._header_tags):
                    break

    @property
    def channels(self):
        if not self._channels and self.parser:
            self.parser.parse_all()
            channels = self.parser.find_one('MYCH')
            for name, data in zip(channels.find('CHNM'), channels.find('FBCA')):
                name = name.string
                data = data.floats
                self._channels[name] = Channel(self, name, data)
        return self._channels


class Channel(object):

    def __init__(self, parent, name, data):
        self.parent = parent
        self.name = name
        self.data = data


if __name__ == '__main__':

    import sys
    cache = Cache(sys.argv[1])
    cache.pprint()

