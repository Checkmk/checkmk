OPENSSL := openssl
# also set in package_versions.bzl
OPENSSL_DIR := $(OPENSSL)

OPENSSL_INSTALL := $(BUILD_HELPER_DIR)/$(OPENSSL_DIR)-install

# externally required variables
OPENSSL_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(OPENSSL_DIR)

$(OPENSSL)-build-library: $(BUILD_HELPER_DIR) $(OPENSSL_CACHE_PKG_PROCESS)

# Used by Python/Python.make
PACKAGE_OPENSSL_DESTDIR := $(OPENSSL_INSTALL_DIR)
PACKAGE_OPENSSL_LDFLAGS := -L$(PACKAGE_OPENSSL_DESTDIR)/lib
PACKAGE_OPENSSL_LD_LIBRARY_PATH := $(PACKAGE_OPENSSL_DESTDIR)/lib
PACKAGE_OPENSSL_INCLUDE_PATH := $(PACKAGE_OPENSSL_DESTDIR)/include

.PHONY: $(OPENSSL_INSTALL)
$(OPENSSL_INSTALL): $(INTERMEDIATE_INSTALL_BAZEL)
	$(RSYNC) --recursive --links --perms "$(OPENSSL_INSTALL_DIR)/" "$(DESTDIR)$(OMD_ROOT)/"
	patchelf --set-rpath "\$$ORIGIN/../lib" \
	    "$(DESTDIR)$(OMD_ROOT)/bin/openssl" \
	    "$(DESTDIR)$(OMD_ROOT)/lib/libssl.so" \
	    "$(DESTDIR)$(OMD_ROOT)/lib/libssl.so.3" \
	    "$(DESTDIR)$(OMD_ROOT)/lib/libcrypto.so" \
	    "$(DESTDIR)$(OMD_ROOT)/lib/libcrypto.so.3"
