import struct
import string


_is_printable = set(string.printable).difference(string.whitespace).__contains__


def hexdump(*args, **kwargs):
    return ''.join(_hexdump(*args, **kwargs))

def _hexdump(raw, initial_offset=0, chunk=4, line=16, indent=''):
    chunk2 = chunk * 2
    line2 = line * 2
    for i in xrange(0, len(raw), line):
        yield indent
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
    def create(cls, tag, *args):
        cls = cls.tag_classes.get(tag, cls)
        return cls(tag, *args)

    def __init__(self, tag, data, offset=None):
        self.tag = tag
        self.data = data
        self.offset = offset
        self.unpacked = self.unpack(data)
        self.value = self.interpret(self.unpacked)

    def pprint(self, _indent):
        print _indent * '    ' + ('%s; %d bytes' % (self.tag, len(self.data)))
        print hexdump(self.data, self.offset, indent=(_indent + 1) * '    ').rstrip()

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


class Group(object):

    def __init__(self, type_, size, start, tag):

        self.type = type_
        self.size = size
        self.start = start
        self.tag = tag

        self.alignment = _get_tag_alignment(self.type)
        self.end = self.start + self.size + _get_padding(self.size, self.alignment)

        self.children = []

    def pprint(self, _indent=0):
        print _indent * '    ' + ('%s group (%s); %d bytes for %d children:' % (self.tag, self.type, self.size, len(self.children)))
        for child in self.children:
            child.pprint(_indent=_indent + 1)



class Parser(object):

    def __init__(self, file):
        self._file = file
        self._group_stack = []
        self.children = []

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
            group = Group(tag, size, offset, group_tag)

            # Add it as a child of the current group.
            group_head = self._group_stack[-1] if self._group_stack else self
            group_head.children.append(group)

            self._group_stack.append(group)

            return group

        else:

            offset = self._file.tell()
            data = self._file.read(size)
            chunk = Chunk.create(tag, data, offset)

            assert self._group_stack, 'Data chunk outside of group.'
            self._group_stack[-1].children.append(chunk)

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
    
    parser = Parser(open(sys.argv[1]))
    parser.parse_all()
    parser.pprint()



