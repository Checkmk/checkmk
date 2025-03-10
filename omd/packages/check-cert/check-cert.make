CHECK_CERT := check-cert
CHECK_CERT_PACKAGE := packages/site/check-cert

CHECK_CERT_BUILD := $(BUILD_HELPER_DIR)/$(CHECK_CERT)-build
CHECK_CERT_INSTALL := $(BUILD_HELPER_DIR)/$(CHECK_CERT)-install

.PHONY: $(CHECK_CERT_BUILD)
$(CHECK_CERT_BUILD):
	bazel build //$(CHECK_CERT_PACKAGE):$(CHECK_CERT) --cmk_version=$(VERSION)

.PHONY: $(CHECK_CERT_INSTALL)
$(CHECK_CERT_INSTALL): $(CHECK_CERT_BUILD)
	install -m 755 $(BAZEL_BIN)/$(CHECK_CERT_PACKAGE)/check-cert $(DESTDIR)$(OMD_ROOT)/lib/nagios/plugins/check_cert
	patchelf --set-rpath "\$$ORIGIN/../../../lib" $(DESTDIR)$(OMD_ROOT)/lib/nagios/plugins/check_cert
	$(TOUCH) $@
