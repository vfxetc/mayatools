import array
import itertools
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


class Parent(object):

    def __init__(self):
        self.children = []
        self.types = {}

    def add_child(self, child):
        self.children.append(child)
        self.types.setdefault(child.tag, []).append(child)

    def find(self, tag):
        for child in self.children:
            if child.tag == tag:
                yield child
            if isinstance(child, Parent):
                for x in child.find(tag):
                    yield x

    def find_one(self, tag, *args):
        for child in self.find(tag):
            return child
        if args:
            return args[0]
        raise KeyError(tag)


class Group(Parent):

    def __init__(self, type_, size, start, tag):
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


class Chunk(object):

    def __init__(self, tag, data, offset=None):
        self.tag = tag
        self.data = data
        self.offset = offset

    def pprint(self, _indent):
        print _indent * '    ' + ('%s; %d bytes' % (self.tag, len(self.data)))
        print hexdump(self.data, self.offset, indent=(_indent + 1) * '    ').rstrip()

    def __repr__(self):
        return '<%s %s; %d bytes>' % (self.__class__.__name__, self.tag, len(self.data))

    def _unpack(self, format_char):
        element_size = struct.calcsize('>' + format_char)
        if len(self.data) % element_size:
           raise ValueError('%s is not multiple of %d for %r format' % (len(self.data), element_size, format_char))
        format_string = '>%d%s' % (len(self.data) / element_size, format_char)
        unpacked = struct.unpack(format_string, self.data)
        return array.array(format_char, unpacked)

    def as_ints(self):
        return self._unpack('L')

    def as_floats(self):
        return self._unpack('f')

    def as_string(self):
        return self.data.rstrip('\0')



class Parser(Parent):

    def __init__(self, file):
        super(Parser, self).__init__()

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
    
    parser = Parser(open(sys.argv[1]))
    parser.parse_all()
    parser.pprint()

    header = parser.find_one('CACH')
    s_time = header.find_one('STIM').as_ints()[0]
    e_time = header.find_one('ETIM').as_ints()[0]
    print 'Time range: %d to %d' % (s_time, e_time)

    channels = parser.find_one('MYCH')
    for name, data in zip(channels.find('CHNM'), channels.find('FBCA')):
        data = data.as_floats()
        print name.as_string(), len(data)




