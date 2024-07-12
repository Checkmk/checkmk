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
BAZEL_BUILD := $(if $(CI),../scripts/run-bazel.sh build,bazel build)

# Bazel paths
BAZEL_BIN := "$(REPO_PATH)/bazel-bin"
BAZEL_BIN_EXT := "$(BAZEL_BIN)/external"

 ifneq ($(filter $(DISTRO_CODE),sles15 sles15sp1 sles15sp2 sles15sp3 sles15sp4),)
	 OPTIONAL_BUILD_ARGS := BAZEL_EXTRA_ARGS="--define git-ssl-no-verify=true"
 endif

# Intermediate Install Target
# intermediate_install used to be necessary to link external dependecies with each other.
# This is now done inside of Bazel
# This target can be removed once `dest` is created inside of Bazel
INTERMEDIATE_INSTALL_BAZEL := '$(BUILD_HELPER_DIR)/intermediate_install_bazel'

# Human make target
.PHONY: intermediate_install_bazel
intermediate_install_bazel: $(INTERMEDIATE_INSTALL_BAZEL)

$(INTERMEDIATE_INSTALL_BAZEL):
	$(OPTIONAL_BUILD_ARGS) $(BAZEL_BUILD) //omd:intermediate_install
	tar -C $(BUILD_BASE_DIR) -xf $(BAZEL_BIN)/omd/intermediate_install.tar.gz

	#TODO: The following code should be executed by Bazel instead of make
	# Fix sysconfigdata
	$(SED) -i "s|/replace-me|$(PACKAGE_PYTHON_DESTDIR)|g" $(PACKAGE_PYTHON_SYSCONFIGDATA)
	# set RPATH for all ELF binaries we find
	find "$(INTERMEDIATE_INSTALL_BASE)/$(PYTHON_DIR)" -maxdepth 2 -type f -exec file {} \; \
	    | grep ELF | cut -d ':' -f1 \
	    | xargs patchelf --set-rpath "\$$ORIGIN/../lib"
	find "$(INTERMEDIATE_INSTALL_BASE)/$(PYTHON_DIR)/lib/python$(PYTHON_MAJOR_DOT_MINOR)/lib-dynload" -name "*.so" -exec file {} \; \
	    | grep ELF | cut -d ':' -f1 \
	    | xargs patchelf --set-rpath "\$$ORIGIN/../.."
	chmod +x $(INTERMEDIATE_INSTALL_BASE)/$(PYTHON_DIR)/bin/pip*

	# This will replace forced absolute paths determined at build time by
	# Bazel/foreign_cc. Note that this step depends on $OMD_ROOT which is different
	# each time
	# Note: Concurrent builds with dependency to OpenSSL seem to trigger the
	#openssl-install-intermediate target simultaneously enough to run into
	#string-replacements which have been done before. So we don't add `--strict`
	# for now
	$(REPO_PATH)/omd/run-pipenv run cmk-dev binreplace \
	    --regular-expression \
	    --inplace \
	    "/home/.*?/openssl.build_tmpdir/openssl/" \
	    "$(OMD_ROOT)/" \
	    "$(OPENSSL_INSTALL_DIR)/lib/libcrypto.so.3"

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
	    PACKAGE_NAME="$$(echo "$*" | sed 's/-[0-9.]\+.*//')"; \
	    PACKAGE_PATH="$(PACKAGE_DIR)/$$PACKAGE_NAME"; \
	    if [ ! -d "$$PACKAGE_PATH" ]; then \
		echo "ERROR: Package directory does not exist" ; \
		exit 1; \
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
	set -e ; DIR=$$($(ECHO) $* | $(SED) 's/-[0-9.]\+.*//'); \
	if [ ! -d "$(PACKAGE_DIR)/$$DIR" ]; then \
	    echo "ERROR: Package directory does not exist" ; \
	    exit 1; \
	fi ; \
	for P in $$($(LS) $(PACKAGE_DIR)/$$DIR/patches/*.dif); do \
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
	echo $(PACKAGE_DIR)

# Include rules to make packages
include \
    packages/openssl/openssl.make \
    packages/redis/redis.make \
    packages/apache-omd/apache-omd.make \
    packages/xinetd/xinetd.make \
    packages/stunnel/stunnel.make \
    packages/check_mk/check_mk.make \
    packages/freetds/freetds.make \
    packages/heirloom-pkgtools/heirloom-pkgtools.make \
    packages/perl-modules/perl-modules.make \
    packages/cpp-libs/cpp-libs.make \
    packages/libgsf/libgsf.make \
    packages/maintenance/maintenance.make \
    packages/mod_fcgid/mod_fcgid.make \
    packages/monitoring-plugins/monitoring-plugins.make \
    packages/check-cert/check-cert.make \
    packages/check-http/check-http.make \
    packages/lcab/lcab.make \
    packages/msitools/msitools.make \
    packages/nagios/nagios.make \
    packages/heirloom-mailx/heirloom-mailx.make \
    packages/navicli/navicli.make \
    packages/nrpe/nrpe.make \
    packages/patch/patch.make \
    packages/pnp4nagios/pnp4nagios.make \
    packages/protobuf/protobuf.make \
    packages/Python/Python.make \
    packages/python3-modules/python3-modules.make \
    packages/omd/omd.make \
    packages/net-snmp/net-snmp.make \
    packages/mod_wsgi/mod_wsgi.make \
    packages/rrdtool/rrdtool.make \
    packages/mk-livestatus/mk-livestatus.make \
    packages/snap7/snap7.make \
    packages/appliance/appliance.make \
    packages/livestatus/livestatus.make \
    packages/neb/neb.make \
    packages/unixcat/unixcat.make \
    packages/xmlsec1/xmlsec1.make \
    packages/robotmk/robotmk.make \
    packages/redfish_mkp/redfish_mkp.make \

ifeq ($(EDITION),enterprise)
include \
    packages/enterprise/enterprise.make
endif
ifeq ($(EDITION),managed)
include \
    packages/enterprise/enterprise.make \
    packages/cloud/cloud.make \
    packages/managed/managed.make
endif
ifeq ($(EDITION),cloud)
include \
    packages/enterprise/enterprise.make \
    packages/cloud/cloud.make
endif
ifeq ($(EDITION),saas)
include \
    packages/enterprise/enterprise.make \
    packages/cloud/cloud.make \
    packages/saas/saas.make
else
# Ship nagvis for all but saas edition: CMK-14926
# also exclude jaeger
include \
    packages/nagvis/nagvis.make \
    packages/jaeger/jaeger.make
endif
