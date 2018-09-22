from __future__ import print_function

import argparse

try:
    from maya import cmds
    import maya.standalone
except ImportError:
    cmds = None

from .renderer import Renderer


def main(argv=None):

    parser = argparse.ArgumentParser(add_help=None)
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-n', '--dry-run', action='store_true')
    opts, args = parser.parse_known_args()

    scene_path = args.pop()

    if opts.dry_run and not opts.verbose:
        print("--dry-run makes no send without --verbose")
        exit(1)

    if not opts.dry_run:

        if not cmds:
            print("Can't run without --dry-run outside of Maya.")
            exit(2)

        # Don't want to re-initialize.
        try:
            cmds.file
        except AttributeError:
            maya.standalone.initialize()

        cmds.file(scene_path, open=True, force=True)

    renderer = None

    def new_renderer(name=None):
        if name is None:
            if opts.dry_run:
                name = 'default'
            else:
                name = cmds.getAttr('defaultRenderGlobals.currentRenderer')
        print("[mayatools.render] Loading {} renderer.".format(name))
        renderer = Renderer(name)
        run_action(renderer['__init__'])
        return renderer

    def run_action(action):
        params = args[:action.num_params]
        args[:action.num_params] = []
        if opts.verbose:
            action.print(*params)
        if not opts.dry_run:
            action(*params)

    while args:

        if args[0] in ('-h', '--help'):
            args.pop(0)
            if renderer:
                renderer.print_help()
            else:
                parser.print_help()
            exit()

        if args[0] in ('-r', '--renderer'):
            args.pop(0)
            name = args.pop(0)
            renderer = new_renderer(name)
            continue

        if not renderer:
            renderer = new_renderer()
            continue

        if args[0].startswith('-') and args[0].lstrip('-') in renderer:
            name = args.pop(0).lstrip('-')
            action = renderer[name]
            run_action(action)
            continue

        break

    if args:
        raise ValueError("Unhandled arguments: {}".format(' '.join(args)))

    renderer = renderer or new_renderer()
    run_action(renderer['__main__'])

    print("[mayatools.render] DONE")

