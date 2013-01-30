import os
import struct
import glob

class ParseError(RuntimeError):
    pass


_get_channels_results = {}


def get_channels(xml_path, memoize=True):
    """Get a list of channel names and their point counts from a Maya MCC cache.
    
    :param str xml_path: The XML file for the given cache.
    :param bool memoize: Use memoization to avoid parsing?
    :return: List of ``(name, size)`` tuples for each channel.
    :raises ParseError:
    
    """
    
    mcc_paths = glob.glob(os.path.join(os.path.dirname(xml_path), os.path.splitext(os.path.basename(xml_path))[0] + 'Frame*.mc'))
    if not mcc_paths:
        raise ParseError('Could not find any *.mc for %r' % xml_path)
    mcc_path = mcc_paths[0]
    stat = os.stat(mcc_path)
    
    # Return memoized results.
    if (mcc_path in _get_channels_results and
        _get_channels_results[mcc_path][0] == stat.st_size and
        _get_channels_results[mcc_path][1] == stat.st_mtime
    ):
        # Return a copy of the list.
        return list(_get_channels_results[mcc_path][2])
    
    fh = open(mcc_path, 'rb')
    
    # File header block.
    tag = fh.read(4)
    if tag != 'FOR4':
        raise RuntimeError('bad FOR4 tag %r @ %x' % (tag, fh.tell()))
    offset = struct.unpack('>i', fh.read(4))[0]
    fh.seek(offset, 1)
    
    # Channel data block.
    tag = fh.read(4)
    if tag != 'FOR4':
        raise RuntimeError('bad FOR4 tag %r @ %x' % (tag, fh.tell()))
    
    # Start of channel data.
    offset = struct.unpack('>i', fh.read(4))[0]
    tag = fh.read(4)
    if tag != 'MYCH':
        raise RuntimeError('bad MYCH tag %r @ %x' % (tag, fh.tell()))
    
    channels = []
    while True:
        
        # Channel name.
        tag = fh.read(4)
        if not tag:
            # We have reached the end of the file, and so we are done.
            break
        if tag != 'CHNM':
            raise RuntimeError('bad CHNM tag %r @ %x' % (tag, fh.tell()))
        name_size = struct.unpack('>i', fh.read(4))[0]
        name = fh.read(name_size)[:-1]

        # The stored name is padded to the next 4-byte boundary.
        mask = 3
        padded = (name_size + mask) & (~mask)
        padding = padded - name_size
        if padding:
            fh.seek(padding, 1)
        
        # Channel size (e.g. point count).
        tag = fh.read(4)
        if tag != 'SIZE':
            raise RuntimeError('bad SIZE tag %r @ %x' % (tag, fh.tell()))
        point_count_size = struct.unpack('>i', fh.read(4))[0]
        if point_count_size != 4:
            raise RuntimeError('bad point_count_size %r @ %x' % (point_count_size, fh.tell()))
        point_count = struct.unpack('>i', fh.read(point_count_size))[0]
        
        channels.append((name, point_count))
        
        # Skip the actual data.
        tag = fh.read(4)
        if tag == 'FVCA':
            fh.seek(3 * 4 * point_count + 4, 1)
        elif tag == 'DVCA':
            fh.seek(3 * 8 * point_count + 4, 1)
        else:
            raise RuntimeError('bad FVCA/DVCA tag %r @ %x' % (tag, fh.tell()))
    
    # Memoize the result.
    _get_channels_results[mcc_path] = (stat.st_size, stat.st_mtime, channels)
    
    return channels

