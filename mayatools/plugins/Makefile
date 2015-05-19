
MAYA_VERSION = 2014

CFLAGS += -g -I$(MAYAINCLUDE)
LDFLAGS  += -L$(MAYALIB) -lOpenMaya -lFoundation

UNAME := $(shell uname -s)
ifeq ($(UNAME),Linux)
	
	MAYAROOT = /opt/autodesk/maya$(MAYA_VERSION)-x64
	MAYALIB	= $(MAYAROOT)/lib
	MAYAINCLUDE = $(MAYAROOT)/include

	EXT = so

	CFLAGS += -DBits64_ -m64 -DUNIX -D_BOOL -DLINUX -DFUNCPROTO -D_GNU_SOURCE \
	          -DLINUX_64 -fPIC \
	          -fno-strict-aliasing -DREQUIRE_IOSTREAM -Wall \
	          -Wno-multichar -Wno-comment -Wno-sign-compare -funsigned-char \
	          -pthread

	CXXFLAGS += $(CFLAGS) -Wno-deprecated -Wno-reorder \
	            -ftemplate-depth-25 -fno-gnu-keywords

	LDFLAGS += $(CXXFLAGS) -Wl,-Bsymbolic

endif
ifeq ($(UNAME),Darwin)

	MAYAROOT = /Applications/Autodesk/maya$(MAYA_VERSION)
	MAYALIB	= $(MAYAROOT)/Maya.app/Contents/MacOS
	MAYAINCLUDE = $(MAYAROOT)/devkit/include

	EXT = bundle

	CFLAGS += -DCC_GNU_ -DOSMac_ -DOSMacOSX_ -DREQUIRE_IOSTREAM \
			  -DOSMac_MachO_ $(ARCH_FLAGS)  -D_LANGUAGE_C_PLUS_PLUS \
			  -include "$(MAYAINCLUDE)/maya/OpenMayaMac.h"

	CXXFLAGS += $(CFLAGS) -fno-gnu-keywords -fpascal-strings

	# LDFLAGS += -fno-gnu-keywords -fpascal-strings \
	# 		   -isysroot /Developer/SDKs/MacOSX10.6.sdk \
	# 		   $(ARCH_FLAGS) -headerpad_max_install_names \
	# 		   -framework System -framework SystemConfiguration \
	# 		   -framework CoreServices -framework Carbon \
	# 		   -framework Cocoa -framework ApplicationServices \
	# 		   -framework IOKit \
	# 		   -bundle

	# Only export the symbols required for loading the plugin, to avoid clashing
	# with any other plugins that get loaded.
	LDFLAGS += -Wl,-exported_symbol,__Z16initializePlugin7MObject \
	           -Wl,-exported_symbol,__Z18uninitializePlugin7MObject


endif

PLUGIN_NAMES = KSNormalLookup
PLUGINS      = $(PLUGIN_NAMES:%=%.$(EXT))




.PHONY: build clean
.DEFAULT: build

build: $(PLUGINS)

%.$(EXT): %.o
	g++ -shared $(LDFLAGS) $^ -o $@

%.o: %.cpp
	g++ -c $(CXXFLAGS) $^ -o $@

clean:
	- rm $(PLUGINS)
