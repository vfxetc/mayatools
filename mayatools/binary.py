import struct
import string


printable = set(string.printable)


group_tags = set()
_tag_alignments = {}

for base in ('FORM', 'CAT ', 'LIST', 'PROP'):
    for char, alignment in (('', 2), ('4', 4), ('8', 8)):
        tag = base[:-len(char)] + char if char else base
        group_tags.add(tag)
        _tag_alignments[tag] = alignment


def tag_alignment(tag):
    return _tag_alignments.get(tag, 2)


def size_padding(size, alignment):
    if size % alignment == 0:
        return 0
    else:
        return alignment - size % alignment


class Chunk(object):

    def __init__(self, tag, data):
        self.tag = tag
        self.data = data

    def __repr__(self):
        return 'Chunk(%r, size=%d)' % (self.tag, len(self.data))


class Group(list):

    def __init__(self, type_, size, start, tag):
        super(Group, self).__init__()

        self.type = type_
        self.size = size
        self.start = start
        self.tag = tag

        self.alignment = tag_alignment(self.type)
        self.end = self.start + self.size + size_padding(self.size, self.alignment)


def parse(file):

    # Make sure that it looks like a Maya file.
    file.seek(0)
    header = file.read(12)
    if len(header) != 12 or header[:4] != 'FOR4' or header[-4:] != 'Maya':
        raise ValueError('Not a Maya file: header=%r' % header)
    file.seek(0)

    groups = []

    while True:

        while groups and groups[-1].end <= file.tell():
            groups.pop(-1)

        # Read a tag and size from the file.
        tag = file.read(4)
        if not tag:
            break

        size = struct.unpack(">L", file.read(4))[0]

        if tag in group_tags:
            # TODO: push this in a group stack.
            start = file.tell()
            group_tag = file.read(4)
            group = Group(tag, size, start, group_tag)
            print 'Start %s (%s) of length %d' % (group_tag, tag, size)

            if groups:
                groups[-1].append(group)

            groups.append(group)

        else:
            data = file.read(size)
            chunk = Chunk(tag, data)
            groups[-1].append(chunk)
            print 'Chunk %s of length %d' % (chunk.tag, len(chunk.data))

            # Hex dump.
            for line_i in xrange(0, size, 16):
                line = data[line_i:line_i + 16]
                encoded = line.encode('hex')
                print '   ',
                for hex_i in xrange(0, len(encoded), 8):
                    print encoded[hex_i:hex_i + 8],
                print ':', ''.join(c if c in printable else '•' for c in line)
            print

            # And padding
            padding = size_padding(size, groups[-1].alignment)
            if padding:
                file.read(padding)



if __name__ == '__main__':
    import sys
    parse(open(sys.argv[1]))



