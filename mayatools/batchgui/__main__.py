import argparse

from . import BatchGuiMaya


parser = argparse.ArgumentParser()
parser.add_argument('python_script')
args = parser.parse_args()


batch = BatchGuiMaya()
batch.execfile(args.python_script)
batch.exit()

