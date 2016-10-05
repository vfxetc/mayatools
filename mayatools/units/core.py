from maya import cmds 


unit_to_fps = {
	
    'game': 15, 
    'film': 24, 
    'pal': 25, 
    'ntsc': 30, 
    'show': 48,  
    'palf': 50, 
    'ntscf': 60,
    '2fps': 2,
    '3fps': 3,
    '4fps': 4,
    '5fps': 5,
    '6fps': 6,
    '8fps': 8,
    '10fps': 10,
    '12fps': 12,
    '16fps': 16,
    '20fps': 20,
    '40fps': 40,
    '75fps': 75,
    '80fps': 80,
    '100fps': 100,
    '120fps': 120,
    '125fps': 125,
    '150fps': 150,
    '200fps': 200,
    '240fps': 240,
    '250fps': 250,
    '300fps': 300,
    '375fps': 375,
    '400fps': 400,
    '500fps': 500,
    '600fps': 600,
    '750fps': 750,
    '1200fps': 1200,
    '1500fps': 1500,
    '2000fps': 2000,
    '3000fps': 3000,
    '6000fps': 6000
}

fps_to_unit = {
    v: k
    for k, v
    in unit_to_fps.iteritems()
}


def get_fps():
    '''
    Gets framerate and returns the unit as integer. 
    '''
    unit = cmds.currentUnit(q=True, time=True)
    try: 
        return unit_to_fps[unit]
    except KeyError: 
        raise ValueError("Unknown framerate. %s" % unit)


def set_fps(fps):
    '''
    Takes an int as an argument and sets the framerate. 
    '''
    try: 
        unit = fps_to_unit[fps]
    except KeyError: 
        raise ValueError("Bad framerate. %s" % fps)
    cmds.currentUnit(time=unit)

