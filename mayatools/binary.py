import struct
import string


_is_printable = set(string.printable).difference(string.whitespace).__contains__


def hexdump(*args, **kwargs):
    return ''.join(_hexdump(*args, **kwargs))

def _hexdump(raw, initial_offset=0, chunk=4, line=16):
    chunk2 = chunk * 2
    line2 = line * 2
    for i in xrange(0, len(raw), line):
        yield '%04x: ' % (i + initial_offset)
        raw_line = raw[i:i + line]
        encoded = raw_line.encode('hex')
        encoded += ' ' * (line2 - len(encoded))
        for j in xrange(0, line2, chunk2):
            yield '%s ' % encoded[j:j + chunk2]
        yield ''.join(c if _is_printable(c) else '.' for c in raw_line)
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


class Chunk(object):

    tag_classes = {}
    format = None

    @classmethod
    def register_tag(cls, subcls):
        cls.tag_classes[subcls.__name__] = subcls

    @classmethod
    def create(cls, tag, data):
        cls = cls.tag_classes.get(tag, cls)
        return cls(tag, data)

    def __init__(self, tag, data):
        self.tag = tag
        self.data = data
        self.unpacked = self.unpack(data)
        self.value = self.interpret(self.unpacked)

    def unpack(self, data):
        if self.format:
            return struct.unpack(self.format, data)
        else:
            return None

    def interpret(self, values):
        return None

    def __repr__(self):
        return '<%s %r size=%d value=%r>' % (self.__class__.__name__, self.tag, len(self.data), self.value)


@Chunk.register_tag
class SIZE(Chunk):
    format = '>L'

    def interpret(self, unpacked):
        return unpacked[0]


@Chunk.register_tag
class CHNM(Chunk):

    def unpack(self, data):
        return data

    def interpret(self, data):
        return data.rstrip('\0')


@Chunk.register_tag
class FBCA(Chunk):

    def unpack(self, data):
        return struct.unpack('>%sf' % (len(data) / 4), data)
    def interpret(self, values):
        return values


class Group(list):

    def __init__(self, type_, size, start, tag):
        super(Group, self).__init__()

        self.type = type_
        self.size = size
        self.start = start
        self.tag = tag

        self.alignment = _get_tag_alignment(self.type)
        self.end = self.start + self.size + _get_padding(self.size, self.alignment)




def parse(file):


    groups = []

    while True:

        while groups and groups[-1].end <= file.tell():
            groups.pop(-1)

        # Read a tag and size from the file.
        tag = file.read(4)
        if not tag:
            break

        size = struct.unpack(">L", file.read(4))[0]

        if tag in _group_tags:
            # TODO: push this in a group stack.
            start = file.tell()
            group_tag = file.read(4)
            group = Group(tag, size, start, group_tag)

            print 'Start %s (%s) of length %d' % (group_tag, tag, size)

            if groups:
                groups[-1].append(group)

            groups.append(group)

        else:

            data_offset = file.tell()
            data = file.read(size)
            chunk = Chunk.create(tag, data)
            groups[-1].append(chunk)

            print chunk #'Chunk %s of length %d' % (chunk.tag, len(chunk.data))
            print hexdump(data, data_offset)

            # And padding
            padding = _get_padding(size, groups[-1].alignment)
            if padding:
                file.read(padding)



if __name__ == '__main__':
    import sys
    parse(open(sys.argv[1]))



