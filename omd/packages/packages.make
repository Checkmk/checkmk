# Paths to necessary Tools
MKDIR := $(shell which mkdir) -p
RSYNC := $(shell which rsync) -a
TOUCH := $(shell which touch)

# Intermediate Install Target
# intermediate_install used to be necessary to link external dependecies with each other.
# This is now done inside of Bazel
# This target can be removed once `dest` is created inside of Bazel
DEPS_INSTALL_BAZEL := '$(BUILD_HELPER_DIR)/deps_install_bazel'

# Human make target
.PHONY: deps_install_bazel
deps_install_bazel: $(DEPS_INSTALL_BAZEL)

$(DEPS_INSTALL_BAZEL):
	# NOTE: this might result in unexpected build behavior, when dependencies of //omd:intermediate_install
	#       are built somewhere else without --define git-ssl-no-verify=true being specified, likely
	#       resulting in different builds
	# IMPORTANT: Keep the executio log file name in sync with what bazel_logs.groovy cleans-up.
	# TODO: Find a better way to sync the generation and its clean up.
	bazel build --cmk_version=$(VERSION) --cmk_edition=$(EDITION) \
	    $(if $(filter sles15%,$(DISTRO_CODE)),--define git-ssl-no-verify=true) \
	    $(if $(filter community,$(EDITION)),--//:repo_license="gpl") \
	    --execution_log_json_file="$(REPO_PATH)/deps_install.json" \
	    //omd:deps_install_$(EDITION)
	$(MKDIR) $(DESTDIR)
	bazel run @zstd//:zstd_cli -- -d -o `pwd`/deps_install_$(EDITION).tar $(BAZEL_BIN)/omd/deps_install_$(EDITION).tar
	tar -C $(DESTDIR) -xf `pwd`/deps_install_$(EDITION).tar

	mkdir -p $(BUILD_HELPER_DIR)/
	touch $@

HUMAN_INSTALL_TARGETS := $(foreach package,$(PACKAGES),$(addsuffix -install,$(package)))

.PHONY: $(HUMAN_INSTALL_TARGETS)

# Provide some targets for convenience: [pkg] instead of /abs/path/to/[pkg]/[pkg]-[version]-install
$(HUMAN_INSTALL_TARGETS): %-install:
# TODO: Can we make this work as real dependency without submake?
	$(MAKE) $($(addsuffix _INSTALL, $(call package_target_prefix,$*)))

# Include rules to make packages
include \
    packages/appliance/appliance.make
