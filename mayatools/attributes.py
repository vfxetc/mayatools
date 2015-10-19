from maya import cmds, mel

from .sdk import om, mobject_from_name
from . import context


def copy_attributes(src_name, dst_name, include=None, prefix=None, connect=False, copy_values=False):

    include = set(include) if include else None

    src_obj = mobject_from_name(src_name)
    src_dep = om.MFnDependencyNode(src_obj)

    dst_obj = mobject_from_name(dst_name)
    dst_dep = om.MFnDependencyNode(dst_obj)

    existing_attrs = set(cmds.listAttr(dst_name))

    with context.selection():

        cmds.select([dst_name], replace=True)

        for attr_name in cmds.listAttr(src_name):

            if include and attr_name not in include:
                continue

            if prefix and not attr_name.startswith(prefix):
                continue

            # Skip any attributes which are part of a multi-attribute unless
            # specifically requested.
            if not include and cmds.attributeQuery(attr_name, node=src_name, listParent=True):
                continue

            attr_obj = src_dep.attribute(attr_name)
            attr_plug = om.MPlug(src_obj, attr_obj)

            # Create the attribute on the destination of it doesn't exist.
            if attr_name not in existing_attrs:
                dst_dep.addAttribute(attr_obj)

            if connect:
                src_attr = src_name + '.' + attr_name
                dst_attr = dst_name + '.' + attr_name

                existing_conn = cmds.connectionInfo(dst_attr, sourceFromDestination=True)
                if existing_conn and existing_conn != src_attr:
                    cmds.warning('Replacing connection from %r to %r' % (existing_conn, dst_attr))
                
                if not existing_conn or existing_conn != src_attr:
                    cmds.connectAttr(src_attr, dst_attr)

            elif copy_values:
                # Evaluate the mel required to copy the values.
                for mel_chunk in attr_plug.getSetAttrCmds():
                    mel.eval(mel_chunk)


