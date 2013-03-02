
CYTHON_SRCS := $(shell find . -name '*.pyx')
C_SRCS := ${CYTHON_SRCS:%.pyx=%.c}

.PHONY: default build cython

default: cython

build: cython
	python setup.py build

cython: ${C_SRCS}

%.c: %.pyx
	cython -o $@ $<
