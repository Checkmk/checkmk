# This package builds the python protobuf module and also protoc (for tests)
PROTOBUF := protobuf
PROTOBUF_VERS := 3.18.1
PROTOBUF_DIR := $(PROTOBUF)-$(PROTOBUF_VERS)
# Increase this to enforce a recreation of the build cache
PROTOBUF_BUILD_ID := 13

PROTOBUF_PATCHING := $(BUILD_HELPER_DIR)/$(PROTOBUF_DIR)-patching
PROTOBUF_CONFIGURE := $(BUILD_HELPER_DIR)/$(PROTOBUF_DIR)-configure
PROTOBUF_UNPACK := $(BUILD_HELPER_DIR)/$(PROTOBUF_DIR)-unpack
PROTOBUF_BUILD := $(BUILD_HELPER_DIR)/$(PROTOBUF_DIR)-build
PROTOBUF_BUILD_PYTHON := $(BUILD_HELPER_DIR)/$(PROTOBUF_DIR)-build-python
PROTOBUF_BUILD_LIBRARY := $(BUILD_HELPER_DIR)/$(PROTOBUF_DIR)-build-library
PROTOBUF_INTERMEDIATE_INSTALL := $(BUILD_HELPER_DIR)/$(PROTOBUF_DIR)-install-intermediate
PROTOBUF_INTERMEDIATE_INSTALL_PYTHON := $(BUILD_HELPER_DIR)/$(PROTOBUF_DIR)-install-intermediate-python
PROTOBUF_INTERMEDIATE_INSTALL_LIBRARY := $(BUILD_HELPER_DIR)/$(PROTOBUF_DIR)-install-intermediate-library
PROTOBUF_CACHE_PKG_PROCESS := $(BUILD_HELPER_DIR)/$(PROTOBUF_DIR)-cache-pkg-process
PROTOBUF_CACHE_PKG_PROCESS_PYTHON := $(BUILD_HELPER_DIR)/$(PROTOBUF_DIR)-cache-pkg-process-python
PROTOBUF_CACHE_PKG_PROCESS_LIBRARY := $(BUILD_HELPER_DIR)/$(PROTOBUF_DIR)-cache-pkg-process-library
PROTOBUF_INSTALL := $(BUILD_HELPER_DIR)/$(PROTOBUF_DIR)-install
PROTOBUF_INSTALL_PYTHON := $(BUILD_HELPER_DIR)/$(PROTOBUF_DIR)-install-python
PROTOBUF_INSTALL_LIBRARY := $(BUILD_HELPER_DIR)/$(PROTOBUF_DIR)-install-library

PROTOBUF_INSTALL_DIR_PYTHON := $(INTERMEDIATE_INSTALL_BASE)/$(PROTOBUF_DIR)-python
PROTOBUF_INSTALL_DIR_LIBRARY := $(INTERMEDIATE_INSTALL_BASE)/$(PROTOBUF_DIR)-library
PROTOBUF_BUILD_DIR := $(PACKAGE_BUILD_DIR)/$(PROTOBUF_DIR)
#PROTOBUF_WORK_DIR := $(PACKAGE_WORK_DIR)/$(PROTOBUF_DIR)

# Used by other OMD packages
PACKAGE_PROTOBUF_DESTDIR         := $(PROTOBUF_INSTALL_DIR_LIBRARY)
PACKAGE_PROTOBUF_LDFLAGS         := -L$(PACKAGE_PROTOBUF_DESTDIR)/lib
PACKAGE_PROTOBUF_LD_LIBRARY_PATH := $(PACKAGE_PROTOBUF_DESTDIR)/lib
PACKAGE_PROTOBUF_INCLUDE_PATH    := $(PACKAGE_PROTOBUF_DESTDIR)/include/google/protobuf
PACKAGE_PROTOBUF_PROTOC_BIN      := $(PACKAGE_PROTOBUF_DESTDIR)/bin/protoc

# Executed from enterprise/core/src/Makefile.am, enterprise/core/src/.f12
# and ./enterprise/Makefile
$(PROTOBUF)-build-library: $(BUILD_HELPER_DIR) $(PROTOBUF_CACHE_PKG_PROCESS_LIBRARY)

# We have a globally defined $(PROTOBUF_UNPACK) target, but we need some special
# handling here, because downloaded archive name does not match the omd package name
$(PROTOBUF_UNPACK): $(PACKAGE_DIR)/$(PROTOBUF)/protobuf-python-$(PROTOBUF_VERS).tar.gz
	$(RM) -r $(PROTOBUF_BUILD_DIR)
	$(MKDIR) $(PACKAGE_BUILD_DIR)
	$(TAR_GZ) $< -C $(PACKAGE_BUILD_DIR)
	$(MKDIR) $(BUILD_HELPER_DIR)
	$(TOUCH) $@

# We have hidden embedded dependency: PATCHING -> UNPACK
$(PROTOBUF_CONFIGURE): $(PROTOBUF_PATCHING)
	cd $(PROTOBUF_BUILD_DIR) && \
	    export LD_LIBRARY_PATH="$(PACKAGE_PYTHON_LD_LIBRARY_PATH)" && \
	    ./configure --prefix=""
	$(TOUCH) $@

$(PROTOBUF_BUILD_LIBRARY): $(PROTOBUF_CONFIGURE)
	cd $(PROTOBUF_BUILD_DIR) && \
	    make -j6 && \
	    `: Hack needed for protoc to be linked statically. Tried a lot of different things to make it ` \
	    `: work with the standard Makefile and libtool stuff, but had no luck. It always ended with a ` \
	    `: protoc with dynamic dependencies on libgcc and libstdc++. And we really need to have a ` \
	    `: statically linked binary at the moment. The following is a hand crafted linker command. ` \
	    `: Let me know in case you got a cleaner approach. ` \
	    cd src && \
	    rm protoc && \
	    echo -e '\nprotoc-static: $(protoc_OBJECTS) $(protoc_DEPENDENCIES) $(EXTRA_protoc_DEPENDENCIES)\n\tg++ -pthread -DHAVE_PTHREAD=1 -DHAVE_ZLIB=1 -Wall -Wno-sign-compare -static-libgcc -static-libstdc++ -s -o protoc google/protobuf/compiler/main.o -lpthread ./.libs/libprotoc.a ./.libs/libprotobuf.a' >> Makefile && \
	    make -j6 protoc-static && \
	    file $(PROTOBUF_BUILD_DIR)/src/protoc | grep ELF >/dev/null && \
	    ldd $(PROTOBUF_BUILD_DIR)/src/protoc | grep -v libstdc++ >/dev/null
	$(TOUCH) $@

$(PROTOBUF_BUILD_PYTHON): $(PROTOBUF_BUILD_LIBRARY) $(PYTHON_CACHE_PKG_PROCESS)
	cd $(PROTOBUF_BUILD_DIR)/python && \
	    export LD_LIBRARY_PATH="$(PACKAGE_PYTHON_LD_LIBRARY_PATH)" && \
	    $(PACKAGE_PYTHON_EXECUTABLE) setup.py build --cpp_implementation
	$(TOUCH) $@

$(PROTOBUF_BUILD): $(PROTOBUF_BUILD_LIBRARY) $(PROTOBUF_BUILD_PYTHON)
	file $(PROTOBUF_BUILD_DIR)/src/protoc | grep ELF >/dev/null
	ldd $(PROTOBUF_BUILD_DIR)/src/protoc | grep -v libstdc++ >/dev/null
	$(TOUCH) $@

$(PROTOBUF_CACHE_PKG_PROCESS): $(PROTOBUF_CACHE_PKG_PROCESS_PYTHON) $(PROTOBUF_CACHE_PKG_PROCESS_LIBRARY)

PROTOBUF_CACHE_PKG_PATH_PYTHON := $(call cache_pkg_path,$(PROTOBUF_DIR)-python,$(PROTOBUF_BUILD_ID))

$(PROTOBUF_CACHE_PKG_PATH_PYTHON):
	$(call pack_pkg_archive,$@,$(PROTOBUF_DIR)-python,$(PROTOBUF_BUILD_ID),$(PROTOBUF_INTERMEDIATE_INSTALL_PYTHON))

$(PROTOBUF_CACHE_PKG_PROCESS_PYTHON): $(PROTOBUF_CACHE_PKG_PATH_PYTHON)
	$(call unpack_pkg_archive,$(PROTOBUF_CACHE_PKG_PATH_PYTHON),$(PROTOBUF_DIR)-python)
	$(call upload_pkg_archive,$(PROTOBUF_CACHE_PKG_PATH_PYTHON),$(PROTOBUF_DIR)-python,$(PROTOBUF_BUILD_ID))
	$(TOUCH) $@

PROTOBUF_CACHE_PKG_PATH_LIBRARY := $(call cache_pkg_path,$(PROTOBUF_DIR)-library,$(PROTOBUF_BUILD_ID))

$(PROTOBUF_CACHE_PKG_PATH_LIBRARY):
	$(call pack_pkg_archive,$@,$(PROTOBUF_DIR)-library,$(PROTOBUF_BUILD_ID),$(PROTOBUF_INTERMEDIATE_INSTALL_LIBRARY))

$(PROTOBUF_CACHE_PKG_PROCESS_LIBRARY): $(PROTOBUF_CACHE_PKG_PATH_LIBRARY)
	$(call unpack_pkg_archive,$(PROTOBUF_CACHE_PKG_PATH_LIBRARY),$(PROTOBUF_DIR)-library)
	$(call upload_pkg_archive,$(PROTOBUF_CACHE_PKG_PATH_LIBRARY),$(PROTOBUF_DIR)-library,$(PROTOBUF_BUILD_ID))
	$(TOUCH) $@

$(PROTOBUF_INTERMEDIATE_INSTALL): $(PROTOBUF_INTERMEDIATE_INSTALL_PYTHON) $(PROTOBUF_INTERMEDIATE_INSTALL_LIBRARY)

$(PROTOBUF_INTERMEDIATE_INSTALL_LIBRARY): $(PROTOBUF_BUILD_LIBRARY)
	file $(PROTOBUF_BUILD_DIR)/src/protoc | grep ELF >/dev/null
	ldd $(PROTOBUF_BUILD_DIR)/src/protoc | grep -v libstdc++ >/dev/null
	make -C $(PROTOBUF_BUILD_DIR) DESTDIR=$(PROTOBUF_INSTALL_DIR_LIBRARY) install
	$(TOUCH) $@

$(PROTOBUF_INTERMEDIATE_INSTALL_PYTHON): $(PROTOBUF_BUILD_PYTHON)
	cd $(PROTOBUF_BUILD_DIR)/python && \
	    export LD_LIBRARY_PATH="$(PACKAGE_PYTHON_LD_LIBRARY_PATH)" && \
	    $(PACKAGE_PYTHON_EXECUTABLE) setup.py install \
	    --cpp_implementation \
	    --root=$(PROTOBUF_INSTALL_DIR_PYTHON) \
	    --prefix=''
	$(TOUCH) $@

$(PROTOBUF_INSTALL): $(PROTOBUF_INSTALL_LIBRARY) $(PROTOBUF_INSTALL_PYTHON)

$(PROTOBUF_INSTALL_LIBRARY): $(PROTOBUF_CACHE_PKG_PROCESS_LIBRARY)
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
	    $(PROTOBUF_INSTALL_DIR_LIBRARY)/ $(DESTDIR)$(OMD_ROOT)/
	$(TOUCH) $@


$(PROTOBUF_INSTALL_PYTHON): $(PROTOBUF_CACHE_PKG_PROCESS_PYTHON)
	$(RSYNC) $(PROTOBUF_INSTALL_DIR_PYTHON)/ $(DESTDIR)$(OMD_ROOT)/
	$(TOUCH) $@
