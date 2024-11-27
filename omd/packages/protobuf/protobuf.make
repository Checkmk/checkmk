# This package builds the python protobuf module and also protoc (for tests)
PROTOBUF := protobuf
PROTOBUF_VERS := 3.20.1
PROTOBUF_DIR := $(PROTOBUF)-$(PROTOBUF_VERS)
# Increase this to enforce a recreation of the build cache
PROTOBUF_BUILD_ID := 7
# The cached package contains the python major/minor version, so include this in the cache name in order to trigger
# a rebuild on a python version change.
PROTOBUF_BUILD_ID := $(PROTOBUF_BUILD_ID)-python$(PYTHON_MAJOR_DOT_MINOR)

PROTOBUF_PATCHING := $(BUILD_HELPER_DIR)/$(PROTOBUF_DIR)-patching
PROTOBUF_CONFIGURE := $(BUILD_HELPER_DIR)/$(PROTOBUF_DIR)-configure
PROTOBUF_UNPACK := $(BUILD_HELPER_DIR)/$(PROTOBUF_DIR)-unpack
PROTOBUF_BUILD := $(BUILD_HELPER_DIR)/$(PROTOBUF_DIR)-build
PROTOBUF_BUILD_PYTHON := $(BUILD_HELPER_DIR)/$(PROTOBUF_DIR)-build-python
PROTOBUF_BUILD_LIBRARY := $(BUILD_HELPER_DIR)/$(PROTOBUF_DIR)-build-library
PROTOBUF_INTERMEDIATE_INSTALL := $(BUILD_HELPER_DIR)/$(PROTOBUF_DIR)-install-intermediate
PROTOBUF_INTERMEDIATE_INSTALL_PYTHON := $(BUILD_HELPER_DIR)/$(PROTOBUF_DIR)-install-intermediate-python
PROTOBUF_INTERMEDIATE_INSTALL_LIBRARY := $(BUILD_HELPER_DIR)/$(PROTOBUF_DIR)-install-intermediate-library
PROTOBUF_INSTALL := $(BUILD_HELPER_DIR)/$(PROTOBUF_DIR)-install
PROTOBUF_INSTALL_PYTHON := $(BUILD_HELPER_DIR)/$(PROTOBUF_DIR)-install-python
PROTOBUF_INSTALL_LIBRARY := $(BUILD_HELPER_DIR)/$(PROTOBUF_DIR)-install-library

PROTOBUF_INSTALL_DIR_PYTHON := $(INTERMEDIATE_INSTALL_BASE)/$(PROTOBUF_DIR)-python
PROTOBUF_INSTALL_DIR_LIBRARY := $(INTERMEDIATE_INSTALL_BASE)/$(PROTOBUF_DIR)-library

# Used by other OMD packages
PACKAGE_PROTOBUF_DESTDIR         := $(PROTOBUF_INSTALL_DIR_LIBRARY)
PACKAGE_PROTOBUF_LDFLAGS         := -L$(PACKAGE_PROTOBUF_DESTDIR)/lib
PACKAGE_PROTOBUF_LD_LIBRARY_PATH := $(PACKAGE_PROTOBUF_DESTDIR)/lib
PACKAGE_PROTOBUF_INCLUDE_PATH    := $(PACKAGE_PROTOBUF_DESTDIR)/include/google/protobuf
PACKAGE_PROTOBUF_PROTOC_BIN      := $(PACKAGE_PROTOBUF_DESTDIR)/bin/protoc

SITE_PACKAGES_PATH_REL := "lib/python$(PYTHON_VERSION_MAJOR).$(PYTHON_VERSION_MINOR)/site-packages/"

.PHONY: $(PROTOBUF_BUILD)
$(PROTOBUF_BUILD):
	$(BAZEL_CMD) build //omd/packages/protobuf:protobuf_tar

$(PROTOBUF)-build-library: $(PROTOBUF_BUILD)
	mkdir -p $(PACKAGE_PROTOBUF_DESTDIR)
	tar -C $(PACKAGE_PROTOBUF_DESTDIR) --strip-components 1 -xf $(BAZEL_BIN)/omd/packages/protobuf/protobuf.tar

$(PROTOBUF_INSTALL): $(PROTOBUF_BUILD)
	tar -C $(DESTDIR)$(OMD_ROOT)/ --strip-components 1 -xf $(BAZEL_BIN)/omd/packages/protobuf/protobuf.tar
