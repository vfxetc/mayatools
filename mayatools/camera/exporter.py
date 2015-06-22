from __future__ import absolute_import

import contextlib
import os
import re
import traceback

from maya import cmds, mel

from sgfs import SGFS
from sgfs.commands.utils import parse_spec
import sgpublish.exporter.maya

from .. import context
from .. import downgrade
from ..transforms import transfer_global_transforms
from ..playblast import screenshot

# Default Nuke Camera Vert Aperture
DNCVA = 18.672
MODULUS = 25.39999962


def run():
    import warnings
    warnings.warn('exporter.run moved to exporterui')
    from .exporterui import run
    run()


def get_nodes_to_export(start):

    # start with all descendents
    to_export = set(cmds.listRelatives(start, allDescendents=True, fullPath=True) or ())

    # recursively get parents from start
    to_check = [start]
    while to_check:
        node = to_check.pop(0)
        if node in to_export:
            continue
        to_export.add(node)
        to_check.extend(cmds.listRelatives(node, allParents=True, fullPath=True) or ())
    
    return list(to_export)


class CameraExporter(sgpublish.exporter.maya.Exporter):

    def __init__(self):
        super(CameraExporter, self).__init__(
            workspace=cmds.workspace(q=True, fullName=True) or None,
            filename_hint=cmds.file(q=True, sceneName=True) or 'camera.ma',
            publish_type='maya_camera',
        )
    
    def export_publish(self, publisher, **kwargs):
        
        # Construct a path.
        path = os.path.join(publisher.directory, os.path.basename(self.filename_hint))
        
        # Make sure it is MayaAscii.
        path = os.path.splitext(path)[0] + '.ma'
        
        # Set the primary path (on Shotgun)
        publisher.path = path
        
        return self._export(publisher.directory, path, **kwargs)
        
        
    def export(self, directory, path, **kwargs):
        
        # Make sure it is MayaAscii.
        path = os.path.splitext(path)[0] + '.ma'
        
        return self._export(directory, path, **kwargs)
        
    def _export(self, directory, path, camera, bake_to_world_space):
        
        export_path = path
        print '# Exporting camera to %s' % path
        
        if not os.path.exists(directory):
            os.makedirs(directory)
        
        # If this is 2013 then export to somewhere temporary.
        maya_version = int(mel.eval('about -version').split()[0])
        if maya_version > 2011:
            export_path = os.path.splitext(path)[0] + ('.%d.ma' % maya_version)
        
        selection = [] if bake_to_world_space else get_nodes_to_export(camera)

        with contextlib.nested(context.delete(), context.selection(), context.attrs({
            camera + '.horizontalFilmOffset': 0,
            camera + '.verticalFilmOffset': 0,
            camera + '.overscan': 1,
        })) as (to_delete, _, _):
            
            if selection:
                cmds.select(selection, replace=True)
            elif selection is not None:
                cmds.select(clear=True)

            # Bake global transforms to a duplicate camera if requested.
            if bake_to_world_space:

                # Determine a name for the new transform; strip namespaces and
                # collapse the heirarchy.
                # '|ns:parent|ns2:child' -> 'parent_child'
                old_transform = cmds.listRelatives(camera, parent=True, fullPath=True)[0]
                export_name = re.sub(r'(^|\|)([^:]+:)?', '_', old_transform).strip('_') + '_world'

                # Duplicate the transform and its children (e.g. the camera),
                # and find the (new) camera that we want to export.
                new_transform = cmds.duplicate(old_transform, name=export_name)[0]
                to_delete.append(new_transform)
                cmds.parent(new_transform, world=True)
                camera = cmds.listRelatives(new_transform, children=True, type='camera', path=True)[0]

                # Bake transforms.
                transfer_global_transforms({new_transform: old_transform})

                # Select everything under the new transform.
                cmds.select(cmds.listRelatives(new_transform, allDescendents=True, path=True), add=True)

            # The `constructionHistory` here is only to avoid a bug that crashes
            # Maya 2013. I have no idea why it does that, but it does. It only
            # seems to happen on the second runthrough of this tool, with no
            # changes inbettween (using the mayatools.debug.enable_verbose_commands
            # reveals an identical code path). Hopefully, this fixes it...
            cmds.file(export_path, type='mayaAscii', exportSelected=True, constructionHistory=False)
            
            # Rewrite the file to work with 2011.
            if maya_version > 2011:
                downgrade.downgrade_to_2011(export_path, path)
            
            self._export_nuke(os.path.splitext(path)[0] + '.nk', camera)




    def _export_nuke(self, path, camera):

        transform = cmds.listRelatives(camera, fullPath=True, parent=True)[0]

        fh = open(path, 'w')

        fh.write('Camera2 {\n')
        fh.write('\tinputs 0\n')

        name = filter(None, transform.split('|'))[-1]
        name = re.sub(r'\W+', '__', name).strip('_')
        fh.write('\tname "%s"\n' % name)

        fh.write('\trot_order XYZ\n')
        fh.write('\tselected true\n')
        fh.write('\txpos 0\n')
        fh.write('\typos 300\n')

        min_time = int(cmds.playbackOptions(q=True, minTime=True))
        max_time = int(cmds.playbackOptions(q=True, maxTime=True) + 1)

        ts = []
        rs = []
        fs = []
        hfas = []
        vfas = []

        with context.suspend_refresh():

            for time in xrange(min_time, max_time):
                cmds.currentTime(time, edit=True)

                ts.append(
                    # We can't just ask for the translation, since it seems to
                    # take the pivot point into account, and there isn't an
                    # obvious (to me) relationship bettween the translate and
                    # pivot info from cmds.xform. Therefor, we extract it from
                    # the full matrix.
                    cmds.xform(transform, q=True, worldSpace=True, matrix=True)[-4:-1]
                )
                rs.append(
                    cmds.xform(transform, q=True, worldSpace=True, rotation=True)
                )
                fs.append(
                    cmds.camera(camera, q=True, focalLength=True)
                )
                hfas.append(
                    cmds.camera(camera, q=True, horizontalFilmAperture=True) * MODULUS
                )
                vfas.append(
                    cmds.camera(camera, q=True, verticalFilmAperture=True) * MODULUS
                )

        fh.write('\ttranslate {\n')
        for i in xrange(3):
            fh.write('\t\t{curve x%d ' % min_time)
            fh.write(' '.join(str(x[i]) for x in ts))
            fh.write('}\n')
        fh.write('\t}\n')

        fh.write('\trotate {\n')
        for i in xrange(3):
            fh.write('\t\t{curve x%d ' % min_time)
            fh.write(' '.join(str(x[i]) for x in rs))
            fh.write('}\n')
        fh.write('\t}\n')

        fh.write('\tfocal {{curve x%d ' % min_time)
        fh.write(' '.join(str(x) for x in fs))
        fh.write('}}\n')

        fh.write('\thaperture {{curve x%d ' % min_time)
        fh.write(' '.join(str(x) for x in hfas))
        fh.write('}}\n')

        fh.write('\tvaperture {{curve x%d ' % min_time)
        fh.write(' '.join(str(x) for x in vfas))
        fh.write('}}\n')

        fh.write('}\n')




def main():

    import argparse
    import logging
    log = logging.getLogger(__name__)

    parser = argparse.ArgumentParser()
    parser.add_argument('--world', action='store_true')
    parser.add_argument('--no-nuke', action='store_true')

    parser.add_argument('-s', '--start', type=int)
    parser.add_argument('-e', '--end', type=int)
    parser.add_argument('-d', '--out-dir')

    parser.add_argument('--publish-link')
    parser.add_argument('--publish-name')

    parser.add_argument('-l', '--list-cameras', action='store_true')
    parser.add_argument('scene')
    parser.add_argument('camera', nargs='?')
    args = parser.parse_args()

    log.info('initializing Maya')
    import maya.standalone
    maya.standalone.initialize()

    log.info('loading file')
    cmds.file(args.scene, open=True)
    log.info('done loading file')

    cameras = cmds.ls(args.camera or '*', type='camera', long=True) or ()
    if args.list_cameras:
        print '\n'.join(cameras)
        return

    if args.camera:
        if not cameras:
            log.error('no cameras matching %s' % args.camera)
            exit(1)
        camera = cameras[0]
        if len(cameras) > 1:
            log.warning('more than one camera matching %s; taking %s' % (args.camera, camera))
    else:
        cameras = [c for c in cameras if c.split('|')[1] not in ('top', 'side', 'persp', 'front')]
        if not cameras:
            log.error('no non-default cameras')
            exit(1)
        camera = cameras[0]
        if len(cameras) > 1:
            log.warning('more than one non-default camera; taking %s' % camera)

    log.info('will export %s' % camera)

    name = args.publish_name or os.path.splitext(os.path.basename(args.scene))[0]
    exporter = CameraExporter()
    if args.publish_link:
        link = parse_spec(SGFS(), args.publish_link)
        print link

        # take a screenshot (on OS X)
        try:
            thumbnail_path = screenshot()
        except RuntimeError:
            thumbnail_path = None

        exporter.publish(link, name, dict(camera=camera, bake_to_world_space=args.world), thumbnail_path=thumbnail_path)
    else:
        directory = args.out_dir or os.path.join(args.scene, '..', 'data', 'camera', name)
        exporter.export(directory=directory, path=directory, camera=camera, bake_to_world_space=args.world)

    log.info('DONE')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        traceback.print_exc()
        os._exit(1)
    else:
        os._exit(0)

