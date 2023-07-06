# This package contains the SNAP 7 library (http://snap7.sourceforge.net/)
SNAP7 := snap7

SNAP7_INSTALL := $(BUILD_HELPER_DIR)/$(SNAP7)-install

$(SNAP7_INSTALL):
	# run the Bazel build process which does all the dependency stuff
	$(BAZEL_BUILD) @$(SNAP7)//:$(SNAP7)
	install -m 644 $(BAZEL_BIN_EXT)/$(SNAP7)/$(SNAP7)/libsnap7.so $(DESTDIR)$(OMD_ROOT)/lib

# The original 7z file is quite large (20MB), because it contains tons of
# executables, but we don't need any of them. An equivalent .tar.gz would almost
# be 60MB. Furthermore, requiring a 7z command at build time on a ton of
# platforms is annoying (adding repos, varying names, etc.), so we repackage the
# 7z file to a standard gzipped tar file.
# TODO: Do this in the SNAP7_WORK_DIR
# The target is currently not in use, might need some update if usage is
# required
# $(SNAP7)-repackage: clean
#     wget https://sourceforge.net/projects/snap7/files/$(SNAP7_VERS)/$(SNAP7_DIR).7z
#     7z x $(SNAP7_DIR).7z
#     GZIP=-9 tar cvzf $(SNAP7_DIR).tar.gz $(SNAP7_DIR)/build $(SNAP7_DIR)/src $(SNAP7_DIR)/*.txt
