# This package contains the SNAP 7 library (http://snap7.sourceforge.net/)
SNAP7 := snap7

SNAP7_INSTALL := $(BUILD_HELPER_DIR)/$(SNAP7)-install

.PHONY: $(SNAP7_INSTALL)
$(SNAP7_INSTALL):
	# run the Bazel build process which does all the dependency stuff
	bazel build @$(SNAP7)//:$(SNAP7)
	install -m 644 $(BAZEL_BIN_EXT)/$(SNAP7)/$(SNAP7)/libsnap7.so $(DESTDIR)$(OMD_ROOT)/lib
