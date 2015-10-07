import traceback

from maya import cmds


def reduce_sets(set_names=None):

    reduced_sets = {}

    if set_names is None:
        set_names = cmds.listSets(allSets=True)

    for set_name in set_names:
        
        try:
            items = cmds.sets(set_name, q=True) or []
        except (ValueError, RuntimeError):
            continue
        
        reduced_sets[set_name] = this_set = {'objects': [], 'attributes': {}}
            
        for item in items:
            if '.' in item:
                obj, attr = item.split('.')
                path = cmds.ls(obj, long=True)[0] + '.' + attr
                try:
                    this_set['attributes'][path] = cmds.getAttr(item)
                except:
                    # We don't want any wierd attributes to give us trouble.
                    cmds.warning(traceback.format_exc())
            else:
                path = cmds.ls(item, long=True)[0]
                this_set['objects'].append(path)

    return reduced_sets

