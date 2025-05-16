ROBOTMK := robotmk

ROBOTMK_BUILD := $(BUILD_HELPER_DIR)/$(ROBOTMK)-build
ROBOTMK_INTERMEDIATE_INSTALL := $(BUILD_HELPER_DIR)/$(ROBOTMK)-install-intermediate
ROBOTMK_INSTALL := $(BUILD_HELPER_DIR)/$(ROBOTMK)-install

ROBOTMK_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(ROBOTMK)
ROBOTMK_BAZEL_OUT := $(BAZEL_BIN_EXT)/_main~_repo_rules~robotmk

.PHONY: $(ROBOTMK_BUILD)
$(ROBOTMK_BUILD):
	bazel build @$(ROBOTMK)//:build

# Keep the paths below in sync with what is displayed in the file download pages.
# For example, after moving the Windows files to a different folder, we would have to adjust the
# download pages accordingly.
.PHONY: $(ROBOTMK_INTERMEDIATE_INSTALL)
$(ROBOTMK_INTERMEDIATE_INSTALL): $(ROBOTMK_BUILD)
	$(MKDIR) $(ROBOTMK_INSTALL_DIR)/share/check_mk/agents/robotmk/linux
	$(MKDIR) $(ROBOTMK_INSTALL_DIR)/share/check_mk/agents/robotmk/windows
	$(MKDIR) $(ROBOTMK_INSTALL_DIR)/share/check_mk/agents/plugins
	$(MKDIR) $(ROBOTMK_INSTALL_DIR)/share/check_mk/agents/windows/plugins
	install -m 755 $(ROBOTMK_BAZEL_OUT)/robotmk_scheduler $(ROBOTMK_BAZEL_OUT)/rcc $(ROBOTMK_INSTALL_DIR)/share/check_mk/agents/robotmk/linux
	install -m 755 $(ROBOTMK_BAZEL_OUT)/robotmk_scheduler.exe $(ROBOTMK_BAZEL_OUT)/rcc.exe $(ROBOTMK_INSTALL_DIR)/share/check_mk/agents/robotmk/windows
	install -m 755 $(ROBOTMK_BAZEL_OUT)/robotmk_agent_plugin $(ROBOTMK_INSTALL_DIR)/share/check_mk/agents/plugins
	install -m 755 $(ROBOTMK_BAZEL_OUT)/robotmk_agent_plugin.exe $(ROBOTMK_INSTALL_DIR)/share/check_mk/agents/windows/plugins

.PHONY: $(ROBOTMK_INSTALL)
$(ROBOTMK_INSTALL): $(ROBOTMK_INTERMEDIATE_INSTALL)
	$(RSYNC) $(ROBOTMK_INSTALL_DIR)/ $(DESTDIR)$(OMD_ROOT)/
