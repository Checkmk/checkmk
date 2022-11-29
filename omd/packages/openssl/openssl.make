OPENSSL := openssl
OPENSSL_VERS := 1.1.1q
OPENSSL_DIR := $(OPENSSL)-$(OPENSSL_VERS)

OPENSSL_BUILD := $(BUILD_HELPER_DIR)/$(OPENSSL_DIR)-build
OPENSSL_INTERMEDIATE_INSTALL := $(BUILD_HELPER_DIR)/$(OPENSSL_DIR)-install-intermediate
OPENSSL_INSTALL := $(BUILD_HELPER_DIR)/$(OPENSSL_DIR)-install
OPENSSL_CACHE_PKG_PROCESS := $(BUILD_HELPER_DIR)/$(OPENSSL_DIR)-cache-pkg-process


# legacy stuff
OPENSSL_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(OPENSSL_DIR)
PACKAGE_OPENSSL_DESTDIR := $(OPENSSL_INSTALL_DIR)

$(OPENSSL_BUILD):
	bazel build @openssl//:build
	$(TOUCH) $@

# legacy stuff
$(OPENSSL_INTERMEDIATE_INSTALL):
	bazel run @openssl//:deploy
	mkdir -p "$(INTERMEDIATE_INSTALL_BASE)/$(OPENSSL_DIR)"
	tar xf "build/by_bazel/openssl/openssl-built.tgz" -C "$(OPENSSL_INSTALL_DIR)"
	$(TOUCH) $@

# legacy stuff
$(OPENSSL_CACHE_PKG_PROCESS): $(OPENSSL_INTERMEDIATE_INSTALL)
	$(TOUCH) $@

# Executed from enterprise/core/src/Makefile.am
$(OPENSSL)-build-library: $(BUILD_HELPER_DIR) $(OPENSSL_CACHE_PKG_PROCESS)

$(OPENSSL_INSTALL):
	bazel run @openssl//:deploy
	tar xf "build/by_bazel/openssl/openssl-built.tgz" -C "$(DESTDIR)$(OMD_ROOT)/"
	$(TOUCH) $@
