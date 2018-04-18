import os
import re
import sys

from . import binary


def detect_version(path):
    ext = os.path.splitext(path)[1]
    if ext == '.ma':
        return detect_ascii_version(path)
    elif ext == '.mb':
        return detect_binary_version(path)
    else:
        raise ValueError("Cannot detect version of {} file.".format(ext))


def detect_ascii_version(path):
    start = open(path).read(1000)
    m = re.search(r'requires maya "(.+?)"', start)
    if not m:
        raise ValueError("Could not find Maya requirement in ascii file.")
    return m.group(1)


def detect_binary_version(path):
    root = binary.parse(open(path))
    vers = root.find_one('VERS')
    return vers.string


if __name__ == '__main__':

    for path in sys.argv[1:]:
        version = detect_version(path)
        print version, path
