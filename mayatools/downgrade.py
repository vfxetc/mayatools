"""

In the current Western X pipeline, some steps are being performed with different
versions of Maya for various reasons. Unfortunately, the version number does
not always move up as scenes move from step to step, so sometimes we must
downgrade while retaining as much information as possible.

The :func:`.downgrade_to_2011` function is being developed as needs see fit to
downgrade ASCII scene files to Maya 2011.

"""


import sys


def downgrade_to_2011(src_path, dst_path):
    """Downgrade the given Maya ASCII scene to version 2011.

    :param str src_path: The scene >2011 to downgrade.
    :param str dst_path: Where to write the 2011 version.

    Currently handles:

    - cameras
    - image planes
    - meshes (roughly)

    """

    if not src_path.endswith('.ma') or not dst_path.endswith('.ma'):
        raise ValueError('can only operate on MayaAscii files')
        
    # Track if the last command was to create an image plane.
    command_block = ()
            
    fh = open(dst_path, 'w')
    for raw_line in open(src_path):
        
        # Skip comments.
        if raw_line.startswith('//'):
            fh.write(raw_line)
            continue
        
        # This will always have one item, but it may be an empty string.
        raw_line = raw_line.rstrip()
        line = raw_line.lstrip('\t')
        indent = len(raw_line) - len(line)
        is_end_of_command = line[-1] == ';'
        line_parts = line.strip().rstrip(';').strip().split() or ['']
        
        # Track what command block we are in.
        is_command_block = raw_line.strip() and not raw_line[0].isspace()
        if is_command_block:
            command_block = tuple(line_parts)
        
        # Strip out some flags.
        if line_parts[0] == 'setAttr':
            try:
                index = line_parts.index('-ch')
                line_parts = line_parts[:index] + line_parts[index + 2:]
            except ValueError:
                pass
        
        # Strip all requires, but add a 2011 requires.
        if command_block[:1] == ('requires', ):
            if line_parts[1] == 'maya':
                line_parts[2] = '"2011"'
            else:
                continue
                
        # Strip '-p' off of image planes.
        if command_block[:2] == ('createNode', 'imagePlane'):
            if is_command_block:
                # Can't have '-p' flag.
                try:
                    index = line_parts.index('-p')
                    line_parts = line_parts[:index] + line_parts[index + 2:]
                except ValueError:
                    pass
            else:
                # A couple attributes no longer exist.
                if (line_parts[0] == 'setAttr' and (
                    line_parts[1] == '".ic"' or
                    line_parts[-1] == '".v"'
                )):
                    continue
        
        # Not entirely sure what this attribute does...
        if command_block[:2] == ('createNode', 'mesh'):
            if line_parts[:2] == ['setAttr', '".vnm"']:
                continue
        
        # Write the transformed line back out.
        fh.write('%s%s%s\n' % (
            '\t' * indent,
            ' '.join(line_parts),
            ';' if is_end_of_command else ''
        ))


def main():
    downgrade_to_2011(*sys.argv[1:])

if __name__ == '__main__':
    main()

