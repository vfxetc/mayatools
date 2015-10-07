import re
import traceback

from maya import cmds


_default_sets = set((
    'defaultLightSet',
    'defaultObjectSet',
    'initialParticleSE',
    'initialShadingGroup',
))


def reduce_sets(set_names=None, include_default_sets=False):

    reduced_sets = {}

    if set_names is None:
        set_names = cmds.ls(sets=True, long=True)

    for set_name in set_names:
        
        if not include_default_sets and set_name in _default_sets:
            continue

        try:
            set_type = cmds.nodeType(set_name)
            items = cmds.sets(set_name, q=True) or []
        except (ValueError, RuntimeError) as e:
            cmds.warning('%s while inspecting set %s: %s' % (e.__type__.__name__, set_name, e))
            continue
        
        reduced_sets[set_name] = this_set = {
            'attributes': {},
            'objects': [],
            'type': set_type,
        }
            
        for item in items:

            m = re.match(r'^([^\.]+)\.([^\[]+)(?:\[(.+?)])?$', item)
            if m:

                obj_name, attr_name, index = m.groups()
                long_attr_name = cmds.ls(obj_name, long=True)[0] + '.' + attr_name

                # Stuff commented here gives you data type and size, but appears
                # useless in practise.
                #first_index = obj_name + '.' + attr_name + ('[0]' if index else '')
                this_set['attributes'][long_attr_name] = this_attr = {
                    #'type': cmds.getAttr(first_index, type=True),
                    #'size': cmds.getAttr(first_index, size=True),
                }

                if index is None:
                    try:
                        this_attr['value'] = cmds.getAttr(item)
                    except:
                        # We don't want any wierd attributes to give us trouble.
                        cmds.warning(traceback.format_exc())
                else:
                    this_attr['indices'] = index.split('][')

            else:
                path = cmds.ls(item, long=True)[0]
                this_set['objects'].append(path)

    return reduced_sets

