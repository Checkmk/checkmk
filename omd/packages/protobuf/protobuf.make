# This package builds the python protobuf module and also protoc (for tests)
PROTOBUF := protobuf
PROTOBUF_VERS := 3.17.3
PROTOBUF_DIR := $(PROTOBUF)-$(PROTOBUF_VERS)
# Increase this to enforce a recreation of the build cache
PROTOBUF_BUILD_ID := 6

PROTOBUF_UNPACK := $(BUILD_HELPER_DIR)/$(PROTOBUF_DIR)-unpack
PROTOBUF_BUILD := $(BUILD_HELPER_DIR)/$(PROTOBUF_DIR)-build
PROTOBUF_BUILD_LIBRARY := $(BUILD_HELPER_DIR)/$(PROTOBUF_DIR)-build-library
PROTOBUF_INTERMEDIATE_INSTALL := $(BUILD_HELPER_DIR)/$(PROTOBUF_DIR)-install-intermediate
PROTOBUF_CACHE_PKG_PROCESS := $(BUILD_HELPER_DIR)/$(PROTOBUF_DIR)-cache-pkg-process
PROTOBUF_INSTALL := $(BUILD_HELPER_DIR)/$(PROTOBUF_DIR)-install

PROTOBUF_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(PROTOBUF_DIR)
PROTOBUF_BUILD_DIR := $(PACKAGE_BUILD_DIR)/$(PROTOBUF_DIR)
#PROTOBUF_WORK_DIR := $(PACKAGE_WORK_DIR)/$(PROTOBUF_DIR)

# Used by other OMD packages
PACKAGE_PROTOBUF_DESTDIR         := $(PROTOBUF_INSTALL_DIR)
PACKAGE_PROTOBUF_LDFLAGS         := -L$(PACKAGE_PROTOBUF_DESTDIR)/lib
PACKAGE_PROTOBUF_LD_LIBRARY_PATH := $(PACKAGE_PROTOBUF_DESTDIR)/lib
PACKAGE_PROTOBUF_INCLUDE_PATH    := $(PACKAGE_PROTOBUF_DESTDIR)/include/google/protobuf
PACKAGE_PROTOBUF_PROTOC_BIN      := $(PACKAGE_PROTOBUF_DESTDIR)/bin/protoc

protobuf-build-library: $(PROTOBUF_BUILD_LIBRARY)

# We have a globally defined $(PROTOBUF_UNPACK) target, but we need some special
# handling here, because downloaded archive name does not match the omd package name
$(PROTOBUF_UNPACK): $(PACKAGE_DIR)/$(PROTOBUF)/protobuf-python-$(PROTOBUF_VERS).tar.gz
	$(RM) -r $(PROTOBUF_BUILD_DIR)
	$(MKDIR) $(PACKAGE_BUILD_DIR)
	$(TAR_GZ) $< -C $(PACKAGE_BUILD_DIR)
	$(MKDIR) $(BUILD_HELPER_DIR)
	$(TOUCH) $@

$(PROTOBUF_BUILD_LIBRARY): $(PROTOBUF_UNPACK)
	cd $(PROTOBUF_BUILD_DIR) && \
	    export LDFLAGS="-static-libgcc -static-libstdc++ -s" \
		`: -fPIC is needed for python static linking ` \
		   CXXFLAGS="-fPIC" \
		   LD_LIBRARY_PATH="$(PACKAGE_PYTHON3_LD_LIBRARY_PATH)" && \
	    ./configure --disable-shared && \
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

$(PROTOBUF_BUILD): $(PYTHON3_CACHE_PKG_PROCESS) $(PROTOBUF_BUILD_LIBRARY)
	file $(PROTOBUF_BUILD_DIR)/src/protoc | grep ELF >/dev/null
	ldd $(PROTOBUF_BUILD_DIR)/src/protoc | grep -v libstdc++ >/dev/null
	cd $(PROTOBUF_BUILD_DIR)/python && \
	    export LDFLAGS="-static-libgcc -static-libstdc++ -s" \
		   CXXFLAGS="-fPIC" \
		   LD_LIBRARY_PATH="$(PACKAGE_PYTHON3_LD_LIBRARY_PATH)" \
		   PATH="$(PACKAGE_PYTHON3_BIN):$$PATH" && \
	    $(PACKAGE_PYTHON3_EXECUTABLE) setup.py build --cpp_implementation --compile_static_extension
	$(TOUCH) $@

PROTOBUF_CACHE_PKG_PATH := $(call cache_pkg_path,$(PROTOBUF_DIR),$(PROTOBUF_BUILD_ID))

$(PROTOBUF_CACHE_PKG_PATH):
	$(call pack_pkg_archive,$@,$(PROTOBUF_DIR),$(PROTOBUF_BUILD_ID),$(PROTOBUF_INTERMEDIATE_INSTALL))

$(PROTOBUF_CACHE_PKG_PROCESS): $(PROTOBUF_CACHE_PKG_PATH)
	$(call unpack_pkg_archive,$(PROTOBUF_CACHE_PKG_PATH),$(PROTOBUF_DIR))
	$(call upload_pkg_archive,$(PROTOBUF_CACHE_PKG_PATH),$(PROTOBUF_DIR),$(PROTOBUF_BUILD_ID))
	$(TOUCH) $@

$(PROTOBUF_INTERMEDIATE_INSTALL): $(PROTOBUF_BUILD)
	file $(PROTOBUF_BUILD_DIR)/src/protoc | grep ELF >/dev/null
	ldd $(PROTOBUF_BUILD_DIR)/src/protoc | grep -v libstdc++ >/dev/null
	mkdir -p $(PROTOBUF_INSTALL_DIR)/bin
	install -m 0750 $(PROTOBUF_BUILD_DIR)/src/protoc $(PACKAGE_PROTOBUF_PROTOC_BIN)
	cd $(PROTOBUF_BUILD_DIR)/python && \
	    export LD_LIBRARY_PATH="$(PACKAGE_PYTHON3_LD_LIBRARY_PATH)" && \
	    $(PACKAGE_PYTHON3_EXECUTABLE) setup.py install \
	    --cpp_implementation \
	    --root=$(PROTOBUF_INSTALL_DIR) \
	    --prefix=''
	$(TOUCH) $@


$(PROTOBUF_INSTALL): $(PROTOBUF_CACHE_PKG_PROCESS)
	$(RSYNC) $(PROTOBUF_INSTALL_DIR)/ $(DESTDIR)$(OMD_ROOT)/
	$(TOUCH) $@
