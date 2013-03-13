import array
import functools
import itertools
import struct
import string


_is_printable = set(string.printable).difference(string.whitespace).__contains__


class Encoder(object):

    def split(self, encoded, size_hint):
        for i in xrange(0, len(encoded), size_hint):
            yield encoded[i:i + size_hint]

    def repr_chunk(self, chunk):
        return ''.join(c if _is_printable(c) else '.' for c in chunk)


class StructEncoder(Encoder):

    def __init__(self, format_char):
        self.format_char = format_char
        self.size = struct.Struct('>' + format_char).size

    def split(self, encoded, size_hint):
        size_hint = size_hint - (size_hint % self.size)
        return super(StructEncoder, self).split(encoded, size_hint)

    def unpack(self, encoded):
        count, rem = divmod(len(encoded), self.size)
        if rem:
            raise ValueError('encoded length %d is not multiple of %d; %d remains' % (len(encoded), self.size, rem))
        return struct.unpack('>%d%s' % (count, self.format_char), encoded)

    def repr_chunk(self, encoded):
        return ' '.join(repr(x) for x in self.unpack(encoded))


class StringEncoder(Encoder):

    def split(self, encoded, size_hint):
        return encoded.rstrip('\0').split('\0')

    def repr_chunk(self, chunk):
        return repr(chunk)


# Map encoding names to the object which exposes the Encoder interface.
encoders = {}


def register_encoder(names, encoder=None):
    """Decorator to register encoders."""
    if isinstance(names, basestring):
        names = [names]
    if encoder is None:
        return functools.partial(register_encoder, names)
    else:
        for name in names:
            encoders[name] = encoder
        return encoder


register_encoder('float', StructEncoder('f'))
register_encoder('uint', StructEncoder('L'))
register_encoder('string', StringEncoder())


# Map tag names to the name of an encoding.
tag_encoding = {
    
    # Maya headers.
    'VERS': 'string', # app version
    'UVER': 'string',
    'MADE': 'string',
    'CHNG': 'string', # timestamp
    'ICON': 'string',
    'INFO': 'string',
    'OBJN': 'string',
    'INCL': 'string',
    'LUNI': 'string', # linear unit
    'TUNI': 'string', # time unit
    'AUNI': 'string', # angle unit
    'FINF': 'string', # file info

    # Generic.
    'SIZE': 'uint',

    # DAG
    'CREA': 'string', # create node
    'STR ': 'string', # string attribute

    # Cache headers.
    'VRSN': 'string', # cache version
    'STIM': 'uint',   # cache start time
    'ETIM': 'uint',   # cache end time

    # Cache channels.
    'CHNM': 'string', # channel name

    # Cache data.
    'FBCA': 'float',  # floating cache array
}


def get_encoder(tag):
    encoding = tag_encoding.get(tag, 'raw')
    return encoders.get(encoding) or Encoder()


def hexdump(*args, **kwargs):
    return ''.join(_hexdump(*args, **kwargs))

def _hexdump(raw, initial_offset=0, chunk=4, line=16, indent='', tag=None):

    chunk2 = 2 * chunk
    line2 = 2 * line
    encoder = get_encoder(tag)
    offset = initial_offset

    for encoded_chunk in encoder.split(raw, line):
        if not encoded_chunk:
            continue

        yield indent
        yield '%04x: ' % offset
        offset += len(encoded_chunk)

        # Encode the chunk to hex, pad it, and chunk it further.
        hex_chunk = encoded_chunk.encode('hex')
        hex_chunk += ' ' * (line2 - len(hex_chunk))
        for i in xrange(0, len(hex_chunk), chunk2):
            yield '%s ' % hex_chunk[i:i + chunk2]

        yield encoder.repr_chunk(encoded_chunk)
        yield '\n'


_group_tags = set()
_tag_alignments = {}

for base in ('FORM', 'CAT ', 'LIST', 'PROP'):
    for char, alignment in (('', 2), ('4', 4), ('8', 8)):
        tag = base[:-len(char)] + char if char else base
        _group_tags.add(tag)
        _tag_alignments[tag] = alignment


def _get_tag_alignment(tag):
    return _tag_alignments.get(tag, 2)


def _get_padding(size, alignment):
    if size % alignment == 0:
        return 0
    else:
        return alignment - size % alignment


class Node(object):

    def __init__(self):
        self.children = []
        self.types = {}

    def add_child(self, child):
        self.children.append(child)
        self.types.setdefault(child.tag, []).append(child)
        child.parent = self
        return child

    def add_group(self, *args, **kwargs):
        return self.add_child(Group(*args, **kwargs))

    def add_chunk(self, *args, **kwargs):
        return self.add_child(Chunk(*args, **kwargs))

    def find(self, tag):
        for child in self.children:
            if child.tag == tag:
                yield child
            if isinstance(child, Node):
                for x in child.find(tag):
                    yield x

    def find_one(self, tag, *args):
        for child in self.find(tag):
            return child
        if args:
            return args[0]
        raise KeyError(tag)

    def dumps_iter(self):
        for child in self.children:
            for x in child.dumps_iter():
                yield x


class Group(Node):

    def __init__(self, tag, type_='FOR4', size=0, start=0):
        super(Group, self).__init__()

        self.type = type_
        self.size = size
        self.start = start
        self.tag = tag

        self.alignment = _get_tag_alignment(self.type)
        self.end = self.start + self.size + _get_padding(self.size, self.alignment)

    def pprint(self, _indent=0):
        print _indent * '    ' + ('%s group (%s); %d bytes for %d children:' % (self.tag, self.type, self.size, len(self.children)))
        for child in self.children:
            child.pprint(_indent=_indent + 1)

    def dumps_iter(self):
        output = []
        for child in self.children:
            output.extend(child.dumps_iter())
        yield self.type
        yield struct.pack(">L", sum(len(x) for x in output) + 4)
        yield self.tag
        for x in output:
            yield x


class Chunk(object):

    def __init__(self, tag, data='', offset=None, **kwargs):
        self.parent = None
        self.tag = tag
        self.data = data
        self.offset = offset
        for k, v in kwargs.iteritems():
            setattr(self, k, v)

    def pprint(self, _indent):
        encoding = tag_encoding.get(self.tag)
        if encoding:
            header = '%d bytes as %s(s)' % (len(self.data), encoding)
        else:
            header = '%d raw bytes' % len(self.data)
        print _indent * '    ' + ('%s; %s' % (self.tag, header))
        print hexdump(self.data, self.offset, tag=self.tag, indent=(_indent + 1) * '    ').rstrip()

    def __repr__(self):
        return '<%s %s; %d bytes>' % (self.__class__.__name__, self.tag, len(self.data))

    def dumps_iter(self):
        yield self.tag
        yield struct.pack(">L", len(self.data))
        yield self.data
        padding = _get_padding(len(self.data), self.parent.alignment)
        if padding:
            yield '\0' * padding

    def _unpack(self, format_char):
        element_size = struct.calcsize('>' + format_char)
        if len(self.data) % element_size:
           raise ValueError('%s is not multiple of %d for %r format' % (len(self.data), element_size, format_char))
        format_string = '>%d%s' % (len(self.data) / element_size, format_char)
        unpacked = struct.unpack(format_string, self.data)
        return array.array(format_char, unpacked)

    def _pack(self, format_char, values):
        self.data = struct.pack('>%d%s' % (len(values), format_char), *values)

    @property
    def ints(self):
        return self._unpack('L')

    @ints.setter
    def ints(self, values):
        self._pack('L', values)

    @property
    def floats(self):
        return self._unpack('f')

    @floats.setter
    def floats(self, values):
        self._pack('f', values)

    @property
    def string(self):
        return self.data.rstrip('\0')

    @string.setter
    def string(self, v):
        self.data = str(v).rstrip('\0') + '\0'


class Parser(Node):

    def __init__(self, file):
        super(Parser, self).__init__()

        self._file = file
        self._group_stack = []
        self.children = []

    def close(self):
        self._file.close()

    def pprint(self, _indent=-1):
        for child in self.children:
            child.pprint(_indent=_indent + 1)

    def parse_next(self):

        # Clean the group stack.
        while self._group_stack and self._group_stack[-1].end <= self._file.tell():
            self._group_stack.pop(-1)

        # Read a tag and size from the file.
        tag = self._file.read(4)
        if not tag:
            return
        size = struct.unpack(">L", self._file.read(4))[0]

        if tag in _group_tags:

            offset = self._file.tell()
            group_tag = self._file.read(4)
            group = Group(group_tag, tag, size, offset)

            # Add it as a child of the current group.
            group_head = self._group_stack[-1] if self._group_stack else self
            group_head.add_child(group)

            self._group_stack.append(group)

            return group

        else:

            offset = self._file.tell()
            data = self._file.read(size)
            chunk = Chunk(tag, data, offset)

            assert self._group_stack, 'Data chunk outside of group.'
            self._group_stack[-1].add_child(chunk)

            # Cleanup padding.
            padding = _get_padding(size, self._group_stack[-1].alignment)
            if padding:
                self._file.read(padding)

            return chunk

    def parse_all(self):
        while self.parse_next() is not None:
            pass


if __name__ == '__main__':
    import sys
    from optparse import OptionParser

    opt_parser = OptionParser()
    opt_parser.add_option('-t', '--type', action='append', default=[])
    opt_parser.add_option('-n', '--no-types', action='store_true')
    opts, args = opt_parser.parse_args()

    if opts.no_types:
        tag_encoding.clear()

    for type_spec in opts.type:
        type_spec = type_spec.split(':')
        names = type_spec[0].split(',')
        if len(type_spec) == 1:
            for name in names:
                tag_encoding.pop(name, None)
        elif len(type_spec) == 2:
            for name in names:
                tag_encoding[name] = type_spec[1]
        else:
            raise ValueError('type spec should look like NAME:type')


    for arg in args:
        parser = Parser(open(arg))
        parser.parse_all()
        parser.pprint()

