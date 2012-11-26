#!/usr/bin/env bash

# Since nose is not installed in the Python environment that is accessble to
# Maya (within the WesternX environment), we need to jump through a couple of
# hoops to make sure it is accessible.

if [[ ! "$MAYA_PYTHON" ]]; then
    MAYA_PYTHON=maya2011_python
fi

function whichpy {
	python <<-EOF
		import os, $1
		path = $1.__file__
		if path.endswith('.pyc'):
		    path = path[:-1]
		if os.path.splitext(path)[0].endswith('__init__'):
		    path = os.path.dirname(path)
		print path
	EOF
}

PYTHONPATH=$(whichpy nose)/..:$PYTHONPATH $MAYA_PYTHON -m nose.core $@
