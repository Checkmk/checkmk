JAEGER := jaeger

JAEGER_BUILD := $(BUILD_HELPER_DIR)/$(JAEGER)-build
JAEGER_INSTALL := $(BUILD_HELPER_DIR)/$(JAEGER)-install
JAEGER_BAZEL_OUT := $(BAZEL_BIN)/omd/packages/$(JAEGER)

.PHONY: $(JAEGER_BUILD)
$(JAEGER_BUILD):
	bazel build //omd/packages/$(JAEGER):extract_binary
	bazel build //omd/packages/$(JAEGER):hooks

.PHONY: $(JAEGER_INSTALL)
$(JAEGER_INSTALL): $(JAEGER_BUILD)
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/bin
	install -m 755 $(JAEGER_BAZEL_OUT)/jaeger $(DESTDIR)$(OMD_ROOT)/bin/jaeger
	install -m 755 $(JAEGER_BAZEL_OUT)/lib/omd/hooks/TRACE_RECEIVE $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks/TRACE_RECEIVE
	install -m 755 $(JAEGER_BAZEL_OUT)/lib/omd/hooks/TRACE_RECEIVE_ADDRESS $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks/TRACE_RECEIVE_ADDRESS
	install -m 755 $(JAEGER_BAZEL_OUT)/lib/omd/hooks/TRACE_RECEIVE_PORT $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks/TRACE_RECEIVE_PORT
	install -m 755 $(JAEGER_BAZEL_OUT)/lib/omd/hooks/TRACE_JAEGER_ADMIN_PORT $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks/TRACE_JAEGER_ADMIN_PORT
	install -m 755 $(JAEGER_BAZEL_OUT)/lib/omd/hooks/TRACE_JAEGER_UI_PORT $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks/TRACE_JAEGER_UI_PORT
