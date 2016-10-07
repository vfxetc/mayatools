import re

from maya import cmds 


# These are all of the named framerates. The rest of them look
# like "100fps".
unit_to_fps = {
    'sec': 1,
    'game': 15, 
    'film': 24, 
    'pal': 25, 
    'ntsc': 30, 
    'show': 48,  
    'palf': 50, 
    'ntscf': 60,
    'millisec': 1000,
    # NOTE: We don't support 'min' or 'hour' here because we return integers.
}

fps_to_unit = {v: k for k, v in unit_to_fps.iteritems()}

valid_fpses = frozenset((

    # The named ones above.
    15, 24, 25, 30, 48, 50, 60, 

    # The rest of the known valid FPSes as of Maya 2016.
    2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 40, 75, 80, 100, 120, 125, 150, 200,
    240, 250, 300, 375, 400, 500, 600, 750, 1200, 1500, 2000, 3000, 6000,

))


def get_fps():
    '''
    Get current framerate as an integer.

    ::
        >>> units.get_fps()
        24

    '''

    unit = cmds.currentUnit(q=True, time=True)
    try: 
        return unit_to_fps[unit]
    except KeyError:
        pass

    m = re.match(r'(\d+)fps', unit)
    if m:
        return int(m.group(1))

    raise ValueError("Unknown Maya time unit %r" % unit)


def set_fps(fps):
    '''
    Set current framerate as an integer.

    :param int fps: The framerate to set.

    ::
        >>> units.set_fps(12)
        >>> units.get_fps()
        12

    '''

    unit = fps_to_unit.get(fps) or ('%dfps' % fps)
    try:
        cmds.currentUnit(time=unit)
    except ValueError:
        raise ValueError("Unsupported framerate %s" % fps)

