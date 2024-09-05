OPENSSL := openssl
# also set in package_versions.bzl
OPENSSL_VERS := 3.0.14
OPENSSL_DIR := $(OPENSSL)-$(OPENSSL_VERS)

OPENSSL_BUILD := $(BUILD_HELPER_DIR)/$(OPENSSL_DIR)-build
OPENSSL_INTERMEDIATE_INSTALL := $(BUILD_HELPER_DIR)/$(OPENSSL_DIR)-install-intermediate
OPENSSL_CACHE_PKG_PROCESS := $(BUILD_HELPER_DIR)/$(OPENSSL_DIR)-cache-pkg-process
OPENSSL_INSTALL := $(BUILD_HELPER_DIR)/$(OPENSSL_DIR)-install

# externally required variables
OPENSSL_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(OPENSSL_DIR)

$(OPENSSL)-build-library: $(BUILD_HELPER_DIR) $(OPENSSL_CACHE_PKG_PROCESS)

# Used by Python/Python.make
PACKAGE_OPENSSL_DESTDIR := $(OPENSSL_INSTALL_DIR)
PACKAGE_OPENSSL_LDFLAGS := -L$(PACKAGE_OPENSSL_DESTDIR)/lib
PACKAGE_OPENSSL_LD_LIBRARY_PATH := $(PACKAGE_OPENSSL_DESTDIR)/lib
PACKAGE_OPENSSL_INCLUDE_PATH := $(PACKAGE_OPENSSL_DESTDIR)/include

.PHONY: $(OPENSSL_BUILD)
$(OPENSSL_BUILD):
	$(BAZEL_BUILD) @openssl//:openssl
	$(MKDIR) $(BUILD_HELPER_DIR)

.PHONY: $(OPENSSL_INTERMEDIATE_INSTALL)
$(OPENSSL_INTERMEDIATE_INSTALL):  $(OPENSSL_BUILD)
	mkdir -p "$(INTERMEDIATE_INSTALL_BASE)/$(OPENSSL_DIR)"
	# This will leave us with some strange file permissions, but works for now, see
	# https://stackoverflow.com/questions/75208034
	$(RSYNC) --recursive --links --times --chmod=u+w "$(BAZEL_BIN_EXT)/openssl/openssl/" "$(OPENSSL_INSTALL_DIR)/"

	# this will replace forced absolute paths determined at build time by
	# Bazel/foreign_cc. Note that this step depends on $OMD_ROOT which is different
	# each time

	# Note: Concurrent builds with dependency to OpenSSL seem to trigger the
	#openssl-install-intermediate target simultaneously enough to run into
	#string-replacements which have been done before. So we don't add `--strict`
	# for now
	../scripts/run-pipenv run cmk-dev binreplace \
	    --regular-expression \
	    --inplace \
	    "/home/.*?/openssl.build_tmpdir/openssl/" \
	    "$(OMD_ROOT)/" \
	    "$(OPENSSL_INSTALL_DIR)/lib/libcrypto.so.3"

# legacy stuff
.PHONY: $(OPENSSL_CACHE_PKG_PROCESS)
$(OPENSSL_CACHE_PKG_PROCESS): $(OPENSSL_INTERMEDIATE_INSTALL)

.PHONY: $(OPENSSL_INSTALL)
$(OPENSSL_INSTALL): $(OPENSSL_CACHE_PKG_PROCESS)
	$(RSYNC) --recursive --links --perms "$(OPENSSL_INSTALL_DIR)/" "$(DESTDIR)$(OMD_ROOT)/"
	patchelf --set-rpath "\$$ORIGIN/../lib" \
	    "$(DESTDIR)$(OMD_ROOT)/bin/openssl" \
	    "$(DESTDIR)$(OMD_ROOT)/lib/libssl.so" \
	    "$(DESTDIR)$(OMD_ROOT)/lib/libssl.so.3" \
	    "$(DESTDIR)$(OMD_ROOT)/lib/libcrypto.so" \
	    "$(DESTDIR)$(OMD_ROOT)/lib/libcrypto.so.3"
