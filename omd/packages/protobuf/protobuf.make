# This package builds the python protobuf module and also protoc (for tests)
PROTOBUF := protobuf
PROTOBUF_DIR := $(PROTOBUF)

PROTOBUF_BUILD := $(BUILD_HELPER_DIR)/$(PROTOBUF_DIR)-build
PROTOBUF_INTERMEDIATE_INSTALL := $(BUILD_HELPER_DIR)/$(PROTOBUF_DIR)-install-intermediate
PROTOBUF_INSTALL := $(BUILD_HELPER_DIR)/$(PROTOBUF_DIR)-install

PROTOBUF_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(PROTOBUF_DIR)

# Used by other OMD packages
PACKAGE_PROTOBUF_DESTDIR         := $(PROTOBUF_INSTALL_DIR_LIBRARY)
PACKAGE_PROTOBUF_LDFLAGS         := -L$(PACKAGE_PROTOBUF_DESTDIR)/lib
PACKAGE_PROTOBUF_LD_LIBRARY_PATH := $(PACKAGE_PROTOBUF_DESTDIR)/lib
PACKAGE_PROTOBUF_INCLUDE_PATH    := $(PACKAGE_PROTOBUF_DESTDIR)/include/google/protobuf
PACKAGE_PROTOBUF_PROTOC_BIN      := $(PACKAGE_PROTOBUF_DESTDIR)/bin/protoc

$(PROTOBUF)-build-library: $(PROTOBUF_INTERMEDIATE_INSTALL)

$(PROTOBUF_BUILD):
	$(BAZEL_BUILD) @$(PROTOBUF)//:$(PROTOBUF)

$(PROTOBUF_INTERMEDIATE_INSTALL): $(PROTOBUF_BUILD)
	$(MKDIR) $(PROTOBUF_INSTALL_DIR)
	$(RSYNC) --chmod=u+w $(BAZEL_BIN_EXT)/$(PROTOBUF)/$(PROTOBUF)/ $(PROTOBUF_INSTALL_DIR)

$(PROTOBUF_INSTALL): $(PROTOBUF_INTERMEDIATE_INSTALL)
# Only install the libraries we really need in run time environment. The
# PROTOBUF_INTERMEDIATE_INSTALL_LIBRARY step above installs the libprotobuf.a
# for building the cmc. However, this is not needed later in runtime environment.
# Also the libprotobuf-lite and libprotoc are not needed. We would normally exclude
# the files from being added to the intermediate package, but since we have the
# requirement for cmc and also want to use the build cache for that step, we need
# to do the filtering here. See CMK-9913.
	$(RSYNC) \
	    --exclude 'libprotobuf.a' \
	    --exclude 'libprotoc*' \
	    --exclude 'libprotobuf-lite.*' \
	    --exclude 'protobuf-lite.pc' \
	    $(PROTOBUF_INSTALL_DIR)/ $(DESTDIR)$(OMD_ROOT)/

