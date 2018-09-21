import os
import xml.etree.ElementTree as etree
import re


def eval_descriptor(renderer='rman', options=()):

    try:
        # TODO: Search for this instead of assuming it is Renderman's.
        xml_path = os.path.join(os.environ['RMSTREE'], 'etc', '%sRenderer.xml' % renderer)
    except KeyError:
        raise RuntimeError('$RMSTREE not set')

    try:
        xml = etree.parse(xml_path)
    except IOError:
        raise ValueError('No Maya renderer for %s' % renderer)

    arg_specs = {}
    for node in xml.iter('mel'):
        arg_specs[node.attrib['n']] = 'mel', int(node.attrib.get('p', 1)), node.attrib['s']
    for node in xml.iter('attr'):
        arg_specs[node.attrib['n']] = 'attr', node.attrib['s']
    for node in xml.iter('attrString'):
        arg_specs[node.attrib['n']] = 'attrString', node.attrib['s']


    node = xml.find('melheader')
    if node is not None:
        mel.eval(node.attrib['s'])

    for option_set in options:

        try:
            arg_spec = arg_specs[option_set[0]]
        except KeyError:
            raise ValueError('unknown option %s' % arg)

        if arg_spec[0] == 'mel':
            source = re.sub(r'%(\d+)', lambda m: str(option_set[int(m.group(1))]), arg_spec[2])
            mel.eval(source)

        elif arg_spec[0] in ('attr', 'attrString'):
            cmds.setAttr(arg_spec[1], option_set[1])

        else:
            raise RuntimeError('unknown arg type %s' % arg_spec)

    node = xml.find('meltrailer')
    if node is not None:
        mel.eval(node.attrib['s'])