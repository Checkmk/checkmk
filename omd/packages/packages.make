# Paths to necessary Tools
ECHO := $(shell which echo)
FIND := $(shell which find)
GCC_SYSTEM := $(shell which gcc)
LN := $(shell which ln)
LS := $(shell which ls)
MKDIR := $(shell which mkdir) -p
MV := $(shell which mv)
PATCH := $(shell which patch)
PERL := $(shell which perl)
RSYNC := $(shell which rsync) -a
SED := $(shell which sed)
TAR_BZ2 := $(shell which tar) xjf
TAR_XZ := $(shell which tar) xJf
TAR_GZ := $(shell which tar) xzf
TEST := $(shell which test)
TOUCH := $(shell which touch)
UNZIP := $(shell which unzip) -o

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
	bazel build --cmk_version=$(VERSION) --cmk_edition=$(EDITION_SHORT) \
	    $(if $(filter sles15%,$(DISTRO_CODE)),--define git-ssl-no-verify=true) \
	    --execution_log_json_file="$(REPO_PATH)/deps_install.json" \
	    //omd:deps_install_$(EDITION_SHORT)
	$(MKDIR) $(DESTDIR)
	tar -C $(DESTDIR) -xf $(BAZEL_BIN)/omd/deps_install_$(EDITION_SHORT).tar.xz

	#TODO: The following code should be executed by Bazel instead of make
	# Fix sysconfigdata
	$(SED) -i "s|/replace-me|$(OMD_ROOT)|g" \
	    $(DESTDIR)/$(OMD_ROOT)/lib/python$(PYTHON_MAJOR_DOT_MINOR)/_sysconfigdata__linux_x86_64-linux-gnu.py

	# pre-compile pyc files enforcing `checked-hash` invalidation
	# note: this is a workaround and should be handled in according Bazel project
	$(DESTDIR)$(OMD_ROOT)/bin/python3 -m compileall \
	    -f \
	    --invalidation-mode=checked-hash \
	    -s "$(DESTDIR)/$(OMD_ROOT)/lib/python$(PYTHON_MAJOR_DOT_MINOR)/" \
	    -x "bad_coding|badsyntax|test/test_lib2to3/data" \
	    "$(DESTDIR)/$(OMD_ROOT)/lib/python$(PYTHON_MAJOR_DOT_MINOR)/"

	# This will replace forced absolute paths determined at build time by
	# Bazel/foreign_cc. Note that this step depends on $OMD_ROOT which is different
	# each time
	# Note: Concurrent builds with dependency to OpenSSL seem to trigger the
	#openssl-install-intermediate target simultaneously enough to run into
	#string-replacements which have been done before. So we don't add `--strict`
	# for now
	$(REPO_PATH)/omd/run-binreplace \
	    --regular-expression \
	    --inplace \
	    "/home/.*?/openssl.build_tmpdir/openssl/" \
	    "$(OMD_ROOT)/" \
	    "$(DESTDIR)$(OMD_ROOT)/lib/libcrypto.so.3"

	mkdir -p $(BUILD_HELPER_DIR)/
	touch $@

HUMAN_INSTALL_TARGETS := $(foreach package,$(PACKAGES),$(addsuffix -install,$(package)))
HUMAN_BUILD_TARGETS := $(foreach package,$(PACKAGES),$(addsuffix -build,$(package)))

.PHONY: $(HUMAN_INSTALL_TARGETS) $(HUMAN_BUILD_TARGETS)

# Provide some targets for convenience: [pkg] instead of /abs/path/to/[pkg]/[pkg]-[version]-install
$(HUMAN_INSTALL_TARGETS): %-install:
# TODO: Can we make this work as real dependency without submake?
	$(MAKE) $($(addsuffix _INSTALL, $(call package_target_prefix,$*)))

$(HUMAN_BUILD_TARGETS): %-build: $(BUILD_HELPER_DIR)
# TODO: Can we make this work as real dependency without submake?
	$(MAKE) $($(addsuffix _BUILD, $(call package_target_prefix,$*)))

# Each package may have a packages/[pkg]/skel directory which contents will be
# packed into destdir/skel. These files will be installed, e.g. [site]/etc/...
# and may contain macros that are replaced during site creation/update.
#
# These files here need to be installed into skel/ before the install target is
# executed, because the install target is allowed to do modifications to the
# files.
$(INSTALL_TARGETS): $(BUILD_HELPER_DIR)/%-install: $(BUILD_HELPER_DIR)/%-skel-dir
$(BUILD_HELPER_DIR)/%-skel-dir: $(PRE_INSTALL)
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/skel
	set -e ; \
	    PACKAGE_NAME="$$(echo "$*" | sed 's/-[0-9.]\+.*//')" ; \
	    if [ -d "$(NON_FREE_PACKAGE_DIR)/$$PACKAGE_NAME" ]; then \
	        PACKAGE_PATH="$(NON_FREE_PACKAGE_DIR)/$$PACKAGE_NAME" ; \
	    elif [ -d "$(PACKAGE_DIR)/$$PACKAGE_NAME" ]; then \
	        PACKAGE_PATH="$(PACKAGE_DIR)/$$PACKAGE_NAME" ; \
	    else \
	        echo "ERROR: Package directory does not exist" ; \
	        exit 1 ; \
	    fi ; \
	    if [ ! -d "$$PACKAGE_PATH" ]; then \
	        echo "ERROR: Package directory does not exist" ; \
	        exit 1 ; \
	    fi ; \
	    if [ -d "$$PACKAGE_PATH/skel" ]; then \
	        tar cf - -C "$$PACKAGE_PATH/skel" \
	            --exclude="BUILD" \
	            --exclude="*~" \
	            --exclude=".gitignore" \
	            --exclude=".f12" \
	            . | tar xvf - -C $(DESTDIR)$(OMD_ROOT)/skel ; \
	    fi

# Rules for patching
$(BUILD_HELPER_DIR)/%-patching: $(BUILD_HELPER_DIR)/%-unpack
	set -e ; DIR=$$($(ECHO) $* | $(SED) 's/-[0-9.]\+.*//') ; \
	if [ -d "$(NON_FREE_PACKAGE_DIR)/$$DIR" ]; then \
	    DIR_PATH="$(NON_FREE_PACKAGE_DIR)/$$DIR" ; \
	elif [ -d "$(PACKAGE_DIR)/$$DIR" ]; then \
	    DIR_PATH="$(PACKAGE_DIR)/$$DIR" ; \
	else \
	    echo "ERROR: Package directory does not exist" ; \
	    exit 1 ; \
	fi ; \
	for P in $$($(LS) $$DIR_PATH/patches/*.dif); do \
	    $(ECHO) "applying $$P..." ; \
	    $(PATCH) -p1 -b -d $(PACKAGE_BUILD_DIR)/$* < $$P ; \
	done
	$(TOUCH) $@

# Rules for unpacking
$(BUILD_HELPER_DIR)/%-unpack: $(PACKAGE_DIR)/*/%.tar.xz
	$(RM) -r $(PACKAGE_BUILD_DIR)/$*
	$(MKDIR) $(PACKAGE_BUILD_DIR)
	$(TAR_XZ) $< -C $(PACKAGE_BUILD_DIR)

	$(MKDIR) $(BUILD_HELPER_DIR)
	$(TOUCH) $@

$(BUILD_HELPER_DIR)/%-unpack: $(PACKAGE_DIR)/*/%.tar.gz
	$(RM) -r $(PACKAGE_BUILD_DIR)/$*
	$(MKDIR) $(PACKAGE_BUILD_DIR)
	$(TAR_GZ) $< -C $(PACKAGE_BUILD_DIR)

	$(MKDIR) $(BUILD_HELPER_DIR)
	$(TOUCH) $@

$(BUILD_HELPER_DIR)/%-unpack: $(PACKAGE_DIR)/*/%.tgz
	$(RM) -r $(PACKAGE_BUILD_DIR)/$*
	$(MKDIR) $(PACKAGE_BUILD_DIR)
	$(TAR_GZ) $< -C $(PACKAGE_BUILD_DIR)

	$(MKDIR) $(BUILD_HELPER_DIR)
	$(TOUCH) $@

$(BUILD_HELPER_DIR)/%-unpack: $(PACKAGE_DIR)/*/%.tar.bz2
	$(RM) -r $(PACKAGE_BUILD_DIR)/$*
	$(MKDIR) $(PACKAGE_BUILD_DIR)
	$(TAR_BZ2) $< -C $(PACKAGE_BUILD_DIR)

	$(MKDIR) $(BUILD_HELPER_DIR)
	$(TOUCH) $@

$(BUILD_HELPER_DIR)/%-unpack: $(PACKAGE_DIR)/*/%.zip
	$(RM) -r $(PACKAGE_BUILD_DIR)/$*
	$(MKDIR) $(PACKAGE_BUILD_DIR)
	$(UNZIP) $< -d $(PACKAGE_BUILD_DIR)

	$(MKDIR) $(BUILD_HELPER_DIR)
	$(TOUCH) $@

debug:
	echo "PACKAGE_DIR: $(PACKAGE_DIR), NON_FREE_PACKAGE_DIR: $(NON_FREE_PACKAGE_DIR)"

# Include rules to make packages
include \
    packages/apache-omd/apache-omd.make \
    packages/check_mk/check_mk.make \
    packages/omd/omd.make \
    packages/appliance/appliance.make \

ifeq ($(EDITION),enterprise)
include \
    packages/enterprise/enterprise.make
endif
ifeq ($(EDITION),managed)
include \
    packages/enterprise/enterprise.make \
    packages/cloud/cloud.make \
    packages/managed/managed.make \
    $(REPO_PATH)/non-free/packages/otel-collector/otel-collector.make
endif
ifeq ($(EDITION),cloud)
include \
    packages/enterprise/enterprise.make \
    packages/cloud/cloud.make \
    $(REPO_PATH)/non-free/packages/otel-collector/otel-collector.make
endif
ifeq ($(EDITION),saas)
include \
    packages/enterprise/enterprise.make \
    packages/cloud/cloud.make \
    packages/saas/saas.make
endif
