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

# Rules for patching
$(BUILD_HELPER_DIR)/%-patching: $(BUILD_HELPER_DIR)/%-unpack 
	set -e ; DIR=$$($(ECHO) $* | $(SED) 's/-[0-9.]\+.*//'); \
	for P in $$($(LS) $(PACKAGE_DIR)/$$DIR/patches/*.dif); do \
	    $(ECHO) "applying $$P..." ; \
	    $(PATCH) -p1 -b -d $* < $$P ; \
	done
	$(TOUCH) $@

# Rules for unpacking 
$(BUILD_HELPER_DIR)/%-unpack: $(PACKAGE_DIR)/*/%.tar.xz
	$(RM) -r $* 
	$(MKDIR) $(BUILD_HELPER_DIR)
	$(TAR_XZ) $<
	$(TOUCH) $@

$(BUILD_HELPER_DIR)/%-unpack: $(PACKAGE_DIR)/*/%.tar.gz
	$(RM) -r $* 
	$(MKDIR) $(BUILD_HELPER_DIR)
	$(TAR_GZ) $<
	$(TOUCH) $@

$(BUILD_HELPER_DIR)/%-unpack: $(PACKAGE_DIR)/*/%.tgz
	$(RM) -r $* 
	$(MKDIR) $(BUILD_HELPER_DIR)
	$(TAR_GZ) $<
	$(TOUCH) $@

$(BUILD_HELPER_DIR)/%-unpack: $(PACKAGE_DIR)/*/%.tar.bz2
	$(RM) -r $* 
	$(MKDIR) $(BUILD_HELPER_DIR)
	$(TAR_BZ2) $<
	$(TOUCH) $@

$(BUILD_HELPER_DIR)/%-unpack: $(PACKAGE_DIR)/*/%.zip
	$(RM) -r $* 
	$(MKDIR) $(BUILD_HELPER_DIR)
	$(UNZIP) $<
	$(TOUCH) $@

debug:
	echo $(PACKAGE_DIR)

# Include rules to make packages
include     packages/apache-omd/apache-omd.make \
    packages/boost/boost.make \
    packages/stunnel/stunnel.make \
    packages/check_mk/check_mk.make \
    packages/check_multi/check_multi.make \
    packages/check_mysql_health/check_mysql_health.make \
    packages/check_oracle_health/check_oracle_health.make \
    packages/dokuwiki/dokuwiki.make \
    packages/freetds/freetds.make \
    packages/heirloom-pkgtools/heirloom-pkgtools.make \
    packages/jmx4perl/jmx4perl.make \
    packages/libgsf/libgsf.make \
    packages/maintenance/maintenance.make \
    packages/mk-livestatus/mk-livestatus.make \
    packages/mod_fcgid/mod_fcgid.make \
    packages/mod_wsgi/mod_wsgi.make \
    packages/monitoring-plugins/monitoring-plugins.make \
    packages/msitools/msitools.make \
    packages/nagios/nagios.make \
    packages/nagvis/nagvis.make \
    packages/heirloom-mailx/heirloom-mailx.make \
    packages/navicli/navicli.make \
    packages/net-snmp/net-snmp.make \
    packages/nrpe/nrpe.make \
    packages/nsca/nsca.make \
    packages/omd/omd.make \
    packages/openhardwaremonitor/openhardwaremonitor.make \
    packages/patch/patch.make \
    packages/perl-modules/perl-modules.make \
    packages/pnp4nagios/pnp4nagios.make \
    packages/Python/Python.make \
    packages/Python3/Python3.make \
    packages/python-modules/python-modules.make \
    packages/re2/re2.make \
    packages/rrdtool/rrdtool.make \
    packages/snap7/snap7.make \
    packages/Webinject/Webinject.make \
    packages/appliance/appliance.make

ifeq ($(EDITION),enterprise)
include $(REPO_PATH)/enterprise/enterprise.make
endif
ifeq ($(EDITION),managed)
include $(REPO_PATH)/enterprise/enterprise.make \
    $(REPO_PATH)/managed/managed.make
endif


