'''
Just a stub for locating Maya plugins.

Normally this file would be the __init__.py of the plugins package, but Maya
would then pick it up as a plugin too.
'''


import os


def get_envvars(realpath=False):

    mayatools_plugins = os.path.abspath(os.path.join(__file__, '..', 'plugins'))
    if realpath:
        mayatools_plugins = os.path.realpath(rmantools)
    
    return {
        'MAYA_PLUG_IN_PATH': [mayatools_plugins],
        # 'XBMLANGPATH': os.path.join(mayatools_plugins, 'icons'),
    }


