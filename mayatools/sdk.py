import maya.api.OpenMaya as om


'''
going from C++ API to python/mel API and vice versa

'''

def mobject_from_name(name):
    sel_list = om.MSelectionList()
    sel_list.add(name)
    return sel_list.getDependNode(0)
