OPENSSL := openssl
OPENSSL_VERS := 1.1.1t
OPENSSL_DIR := $(OPENSSL)-$(OPENSSL_VERS)

OPENSSL_BUILD := $(BUILD_HELPER_DIR)/$(OPENSSL_DIR)-build
OPENSSL_INTERMEDIATE_INSTALL := $(BUILD_HELPER_DIR)/$(OPENSSL_DIR)-install-intermediate
OPENSSL_CACHE_PKG_PROCESS := $(BUILD_HELPER_DIR)/$(OPENSSL_DIR)-cache-pkg-process
OPENSSL_INSTALL := $(BUILD_HELPER_DIR)/$(OPENSSL_DIR)-install

# externally required variables
OPENSSL_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(OPENSSL_DIR)

# Executed from enterprise/core/src/Makefile.am
$(OPENSSL)-build-library: $(BUILD_HELPER_DIR) $(OPENSSL_CACHE_PKG_PROCESS)

# Used by Python/Python.make
ifeq ($(DISTRO_CODE),el8)
PACKAGE_OPENSSL_DESTDIR := /usr
else
PACKAGE_OPENSSL_DESTDIR := $(OPENSSL_INSTALL_DIR)
PACKAGE_OPENSSL_LDFLAGS := -L$(PACKAGE_OPENSSL_DESTDIR)/lib
PACKAGE_OPENSSL_LD_LIBRARY_PATH := $(PACKAGE_OPENSSL_DESTDIR)/lib
PACKAGE_OPENSSL_INCLUDE_PATH := $(PACKAGE_OPENSSL_DESTDIR)/include
endif


ifeq ($(DISTRO_CODE),el8)
$(OPENSSL_BUILD):
	$(MKDIR) $(BUILD_HELPER_DIR)
	$(TOUCH) $@
else
$(OPENSSL_BUILD):
	$(BAZEL_BUILD) @openssl//:openssl
	$(MKDIR) $(BUILD_HELPER_DIR)
	$(TOUCH) $@
endif


ifeq ($(DISTRO_CODE),el8)
$(OPENSSL_INTERMEDIATE_INSTALL): $(OPENSSL_BUILD)
	$(MKDIR) $(OPENSSL_INSTALL_DIR)
	$(TOUCH) $@
else
$(OPENSSL_INTERMEDIATE_INSTALL):  $(OPENSSL_BUILD)
	mkdir -p "$(INTERMEDIATE_INSTALL_BASE)/$(OPENSSL_DIR)"
	# This will leave us with some strange file permissions, but works for now, see
	# https://stackoverflow.com/questions/75208034
	rsync -r --chmod=u+w "bazel-bin/external/openssl/openssl/" "$(OPENSSL_INSTALL_DIR)/"
	$(TOUCH) $@
endif


# legacy stuff
$(OPENSSL_CACHE_PKG_PROCESS): $(OPENSSL_INTERMEDIATE_INSTALL)
	$(TOUCH) $@


ifeq ($(DISTRO_CODE),el8)
$(OPENSSL_INSTALL): $(OPENSSL_CACHE_PKG_PROCESS)
	$(TOUCH) $@
else
$(OPENSSL_INSTALL): $(OPENSSL_CACHE_PKG_PROCESS)
	rsync -r --perms "$(OPENSSL_INSTALL_DIR)/" "$(DESTDIR)$(OMD_ROOT)/"
	patchelf --set-rpath "\$$ORIGIN/../lib" \
	    "$(DESTDIR)$(OMD_ROOT)/bin/openssl" \
	    "$(DESTDIR)$(OMD_ROOT)/lib/libssl.so" \
	    "$(DESTDIR)$(OMD_ROOT)/lib/libssl.so.1.1" \
	    "$(DESTDIR)$(OMD_ROOT)/lib/libcrypto.so" \
	    "$(DESTDIR)$(OMD_ROOT)/lib/libcrypto.so.1.1"
	$(TOUCH) $@
endif
