from __future__ import print_function

import argparse

try:
    from maya import cmds
    import maya.standalone
except ImportError:
    cmds = None

from .renderer import Renderer, MelAction


def main(argv=None):

    parser = argparse.ArgumentParser(add_help=None)
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-n', '--dry-run', action='store_true')
    opts, args = parser.parse_known_args()

    scene_path = args.pop()

    opts.verbose = opts.verbose or opts.dry_run

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
            print("[mayatools.render] {}: {}".format(action.name, action.format(*params)))
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

        
        if args[0].startswith('-'):
            
            arg = args.pop(0)

            if arg == '--mel':
                action = MelAction(s=args.pop(0))

            else:

                if arg.startswith('--'):
                    name = arg[2:]
                    if '=' in name:
                        name, next_arg = name.split('=', 1)
                        args.insert(0, next_arg)

                else:
                    name = arg[1]
                    if len(arg) > 2:
                        if renderer[name].num_params:
                            args.insert(0, arg[2:])
                        else:
                            args.insert(0, '-' + arg[2:])

                action = renderer[name]
            
            run_action(action)
            continue

        break

    if args:
        raise ValueError("Unhandled arguments: {}".format(' '.join(args)))

    renderer = renderer or new_renderer()
    run_action(renderer['__main__'])

    print("[mayatools.render] DONE")

