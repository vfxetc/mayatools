import re

from maya import cmds


def get_all_sound_nodes():
    return cmds.ls(type='audio') or ()


def get_saved_sound_node():

    if not cmds.objExists('uiConfigurationScriptNode'):
        raise ValueError('No uiConfigurationScriptNode.')

    source = cmds.getAttr('uiConfigurationScriptNode.before') or ''
    m = re.search(r'^\s*timeControl(?:\s+.+?)? -sound (\w+)(?:\s+.+\s*)?;\s*$', source, flags=re.MULTILINE)
    if not m:
        return

    node = m.group(1)
    return node


def get_active_sound_node():
    
    if cmds.about(batch=True):
        return get_saved_sound_node()

    try:
        playback_slider = mel.eval('$tmpVar = $gPlayBackSlider')
    except RuntimeError:
        playback_slider = None
    if not playback_slider:
        raise ValueError('No $gPlayBackSlider.')

    node = cmds.timeControl(playback_slider, query=True, sound=True)
    return node
