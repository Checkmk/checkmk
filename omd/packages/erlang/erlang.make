ERLANG := erlang

ERLANG_BUILD := $(BUILD_HELPER_DIR)/$(ERLANG)-build
ERLANG_INSTALL := $(BUILD_HELPER_DIR)/$(ERLANG)-install
ERLANG_PLACEHOLDER := /replace-me-erlang
ERLANG_BAZEL_OUT := $(BAZEL_BIN)/external/$(ERLANG)/$(ERLANG)/$(ERLANG_PLACEHOLDER)

.PHONY: $(ERLANG_BUILD)
$(ERLANG_BUILD):
	$(BAZEL_CMD) build @$(ERLANG)//:erlang

.PHONY: $(ERLANG_INSTALL)
$(ERLANG_INSTALL): $(ERLANG_BUILD)
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/bin
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib
	# rsync while excluding some files to reduce the overall size, inspired by
	# https://github.com/rabbitmq/rabbitmq-server/blob/03885faabff311b4be5b627b6c80d4f79c471339/packaging/docker-image/Dockerfile#L185
	$(RSYNC) --chmod=u+w $(ERLANG_BAZEL_OUT)/bin/ $(DESTDIR)$(OMD_ROOT)/bin/
	$(RSYNC) --chmod=u+w --exclude "Install" --exclude "examples" --exclude "misc" $(ERLANG_BAZEL_OUT)/lib/erlang $(DESTDIR)$(OMD_ROOT)/lib/
	ls -lisa $(DESTDIR)$(OMD_ROOT)/lib/erlang/bin/
	ls -lisa $(DESTDIR)$(OMD_ROOT)/lib/erlang/erts-14.2.5.2/bin/
	$(SED) -i "s|$(ERLANG_PLACEHOLDER)|$(OMD_ROOT)|g" $(DESTDIR)$(OMD_ROOT)/lib/erlang/bin/erl
	$(SED) -i "s|$(ERLANG_PLACEHOLDER)|$(OMD_ROOT)|g" $(DESTDIR)$(OMD_ROOT)/lib/erlang/bin/start
	$(SED) -i "s|$(ERLANG_PLACEHOLDER)|$(OMD_ROOT)|g" $(DESTDIR)$(OMD_ROOT)/lib/erlang/erts-14.2.5.2/bin/erl
	$(SED) -i "s|$(ERLANG_PLACEHOLDER)|$(OMD_ROOT)|g" $(DESTDIR)$(OMD_ROOT)/lib/erlang/erts-14.2.5.2/bin/start
