from __future__ import absolute_import

import os
import re
import traceback

from maya import cmds, mel

from mayatools.playblast import screenshot
from sgfs import SGFS
from sgfs.commands.utils import parse_spec
import metatools.deprecate
import qbfutures.maya
import sgpublish.exporter.maya

from .utils import export_cache


def run():
    import warnings
    warnings.warn('exporter.run moved to exporterui')
    from .exporterui import run
    run()


def cache_name_from_cache_set(path):
    name_parts = path.split(':')
    name_parts[-1] = name_parts[-1].replace('cache', '_')
    name_parts = [re.sub(r'[\W_]+', '_', x).strip('_') for x in name_parts]
    name_parts[-1] = '_' + name_parts[-1]
    return '_'.join(name_parts).strip('_')


class Exporter(sgpublish.exporter.maya.Exporter):

    def __init__(self):
        super(Exporter, self).__init__(
            workspace=cmds.workspace(q=True, fullName=True) or None,
            filename_hint=cmds.file(q=True, sceneName=True) or 'geocache.mb',
            publish_type='maya_geocache',
        )

    def add_path_to_work(self, directory, to_cache):
        for members, name, frame_from, frame_to, world in to_cache:
            yield members, os.path.join(directory, name), name, frame_from, frame_to, world

    def export_publish(self, publish, **kwargs):
        # Set the path to the directory.
        publish.path = publish.directory
        kwargs['name'] = '%s - v%04d' % (publish.name, publish.version)
        self.export(publish.directory, publish.path, **kwargs)

    def export(self, directory, path, to_cache, on_farm=False, as_abc=True, name=None):

        if not os.path.exists(directory):
            os.makedirs(directory)

        # Save the scene itself into the directory.
        src_path = cmds.file(q=True, sceneName=True)
        src_ext = os.path.splitext(src_path)[1]
        dst_path = os.path.join(directory, os.path.basename(src_path))
        maya_type = 'mayaBinary' if src_ext == '.mb' else 'mayaAscii'
        try:
            cmds.file(rename=dst_path)
            cmds.file(save=True, type=maya_type)
        finally:
            cmds.file(rename=src_path)

        # Add the path.
        to_cache = self.add_path_to_work(path, to_cache)

        if on_farm:

            executor = qbfutures.maya.Executor(
                cpus=4,
                clone_environ=True,
                create_tempfile=True,
            )
            
            with executor.batch('Geocache Export - %s' % (name or os.path.basename(path))) as batch:
                for args in to_cache:
                    members, path, name, frame_from, frame_to, world = args
                    batch.submit_ext(export_cache, args=args, kwargs={'as_abc': as_abc}, name=str(name))
            
            QtGui.QMessageBox.information(None, "Submitted to Qube", "The geocache export was submitted as job %d" % batch.futures[0].job_id)

        if not on_farm:
            for args in to_cache:
                export_cache(*args, as_abc=as_abc)


def main(argv=None):

    import argparse
    import logging
    log = logging.getLogger(__name__)

    parser = argparse.ArgumentParser()
    parser.add_argument('--no-world', action='store_true')
    parser.add_argument('--no-abc', action='store_true')
    parser.add_argument('-s', '--start', type=int)
    parser.add_argument('-e', '--end', type=int)
    parser.add_argument('-d', '--out-dir')

    parser.add_argument('--publish-link')
    parser.add_argument('--publish-name')
    parser.add_argument('--publish-thumbnail')

    parser.add_argument('-l', '--list-sets', action='store_true')
    parser.add_argument('scene')
    parser.add_argument('cache_sets', nargs='*')
    args = parser.parse_args(argv)

    log.info('initializing Maya')
    import maya.standalone
    maya.standalone.initialize()

    log.info('loading file')
    cmds.file(args.scene, open=True)
    log.info('done loading file')

    cache_sets = set(cmds.ls(*(args.cache_sets or ['__cache__*']), sets=True, recursive=True, long=True) or ())
    if args.list_sets:
        print '\n'.join(sorted(cache_sets))
        return

    frame_from = args.start or cmds.playbackOptions(q=True, animationStartTime=True)
    frame_to   = args.end   or cmds.playbackOptions(q=True, animationEndTime=True)
    
    world = not args.no_world
    as_abc = not args.no_abc

    to_cache = []
    for cache_set in cache_sets:
        members = cmds.sets(cache_set, q=True)
        name = cache_name_from_cache_set(cache_set) or 'cache'
        to_cache.append((members, name, frame_from, frame_to, world))

    name = args.publish_name or os.path.splitext(os.path.basename(args.scene))[0]
    exporter = Exporter()
    if args.publish_link:
        link = parse_spec(SGFS(), args.publish_link)

        # TODO: take a screenshot (on OS X) via screenshot
        thumbnail_path = args.publish_thumbnail
        
        exporter.publish(link, name, dict(to_cache=to_cache, as_abc=as_abc), thumbnail_path=thumbnail_path)
    else:
        directory = args.out_dir or os.path.join(args.scene, '..', 'data', 'geo_cache', name)
        exporter.export(directory=directory, path=directory, to_cache=to_cache, as_abc=as_abc)

    log.info('DONE')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        traceback.print_exc()
        os._exit(1)
    else:
        os._exit(0)

