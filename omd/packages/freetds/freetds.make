FREETDS_DIR := freetds

FREETDS_BUILD := $(BUILD_HELPER_DIR)/$(FREETDS_DIR)-build
FREETDS_INTERMEDIATE_INSTALL := $(BUILD_HELPER_DIR)/$(FREETDS_DIR)-install-intermediate
FREETDS_CACHE_PKG_PROCESS := $(BUILD_HELPER_DIR)/$(FREETDS_DIR)-cache-pkg-process
FREETDS_INSTALL := $(BUILD_HELPER_DIR)/$(FREETDS_DIR)-install

# externally required variables
FREETDS_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(FREETDS_DIR)

# Used by python-modules/python3-modules
PACKAGE_FREETDS_DESTDIR := $(FREETDS_INSTALL_DIR)/build
PACKAGE_FREETDS_LDFLAGS := -L$(PACKAGE_FREETDS_DESTDIR)/lib


$(FREETDS_BUILD): packages/freetds/BUILD.freetds.bazel packages/freetds/freetds.make
	$(BAZEL_BUILD) @freetds//:freetds
	$(MKDIR) $(BUILD_HELPER_DIR)
	$(TOUCH) $@


$(FREETDS_INTERMEDIATE_INSTALL): $(FREETDS_BUILD)
	# Package python-modules needs some stuff during the build.
	$(MKDIR) $(PACKAGE_FREETDS_DESTDIR)
	$(RSYNC) -r --chmod=u+w "$(BAZEL_BIN_EXT)/freetds/freetds/" "$(PACKAGE_FREETDS_DESTDIR)/"
	#
	# At runtime we need only the libraries.
	$(MKDIR) $(FREETDS_INSTALL_DIR)/runtime
	$(RSYNC) -r --exclude=libct* --chmod=u+w "$(BAZEL_BIN_EXT)/freetds/freetds/lib" "$(FREETDS_INSTALL_DIR)/runtime/"
	patchelf --set-rpath "\$$ORIGIN/../lib" \
	    "$(FREETDS_INSTALL_DIR)/runtime/lib/libsybdb.so" \
	    "$(FREETDS_INSTALL_DIR)/runtime/lib/libsybdb.so.5" \
	    "$(FREETDS_INSTALL_DIR)/runtime/lib/libsybdb.so.5.1.0"
	$(TOUCH) $@


$(FREETDS_CACHE_PKG_PROCESS): $(FREETDS_INTERMEDIATE_INSTALL)
	$(TOUCH) $@


$(FREETDS_INSTALL): $(FREETDS_CACHE_PKG_PROCESS)
	$(RSYNC) $(FREETDS_INSTALL_DIR)/runtime/ $(DESTDIR)$(OMD_ROOT)/
	$(TOUCH) $@
