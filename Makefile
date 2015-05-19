.PHONY: build clean
.DEFAULT: build

build:
	make -C mayatools/plugins
clean:
	make -C mayatools/plugins clean

