# xmlsec1 is a dependency of the pysaml2 Python package, which is used for SSO
# via SAML2.0.
# https://www.aleksey.com/xmlsec/

XMLSEC1 := xmlsec1
XMLSEC1_VERS := 1.3.0
XMLSEC1_DIR := $(XMLSEC1)-$(XMLSEC1_VERS)

XMLSEC1_BUILD := $(BUILD_HELPER_DIR)/$(XMLSEC1_DIR)-build
XMLSEC1_INSTALL := $(BUILD_HELPER_DIR)/$(XMLSEC1_DIR)-install

XMLSEC1_BUILD_DIR := $(PACKAGE_BUILD_DIR)/$(XMLSEC1_DIR)

.PHONY: $(XMLSEC1_BUILD)
$(XMLSEC1_BUILD): $(XMLSEC1_UNPACK) $(OPENSSL_CACHE_PKG_PROCESS)
	bazel build @$(XMLSEC1)//:$(XMLSEC1)

.PHONY: $(XMLSEC1_INSTALL)
$(XMLSEC1_INSTALL): $(XMLSEC1_BUILD)
	$(RSYNC) -r --chmod=u+w "$(BAZEL_BIN_EXT)/_main~_repo_rules~xmlsec1/xmlsec1/" "$(DESTDIR)$(OMD_ROOT)/"
	patchelf --set-rpath "\$$ORIGIN/../lib" \
	    "$(DESTDIR)$(OMD_ROOT)/bin/xmlsec1" \
	    "$(DESTDIR)$(OMD_ROOT)/lib/libxmlsec1.so" \
	    "$(DESTDIR)$(OMD_ROOT)/lib/libxmlsec1.so.1" \
	    "$(DESTDIR)$(OMD_ROOT)/lib/libxmlsec1-openssl.so" \
	    "$(DESTDIR)$(OMD_ROOT)/lib/libxmlsec1-openssl.so.1"
