MOD_WSGI := mod_wsgi
MOD_WSGI_DIR := $(MOD_WSGI)

MOD_WSGI_BUILD := $(BUILD_HELPER_DIR)/$(MOD_WSGI_DIR)-build
MOD_WSGI_INSTALL := $(BUILD_HELPER_DIR)/$(MOD_WSGI_DIR)-install

.PHONY: $(MOD_WSGI_BUILD)
$(MOD_WSGI_BUILD):
	$(BAZEL_CMD) build @$(MOD_WSGI)//:$(MOD_WSGI)

.PHONY: $(MOD_WSGI_INSTALL)
$(MOD_WSGI_INSTALL): $(MOD_WSGI_BUILD)
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib/apache/modules
	install -m 644 $(BAZEL_BIN_EXT)/$(MOD_WSGI)/$(MOD_WSGI)/lib/mod_wsgi.so $(DESTDIR)/$(OMD_ROOT)/lib/apache/modules/mod_wsgi.so
