JMX4PERL := jmx4perl
JMX4PERL_VERS := 1.11
JOLOKIA_VERSION := 1.2.3
JMX4PERL_DIR := $(JMX4PERL)-$(JMX4PERL_VERS)

JMX4PERL_UNPACK := $(BUILD_HELPER_DIR)/$(JMX4PERL_DIR)-unpack
JMX4PERL_BUILD := $(BUILD_HELPER_DIR)/$(JMX4PERL_DIR)-build
JMX4PERL_INSTALL := $(BUILD_HELPER_DIR)/$(JMX4PERL_DIR)-install

#JMX4PERL_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(JMX4PERL_DIR)
JMX4PERL_BUILD_DIR := $(PACKAGE_BUILD_DIR)/$(JMX4PERL_DIR)
#JMX4PERL_WORK_DIR := $(PACKAGE_WORK_DIR)/$(JMX4PERL_DIR)

$(JMX4PERL_BUILD): $(JMX4PERL_UNPACK) $(PERL_MODULES_INTERMEDIATE_INSTALL)
	export PERL5LIB=$(PACKAGE_PERL_MODULES_PERL5LIB); \
	    cd $(JMX4PERL_BUILD_DIR) && $(PERL) Build.PL < /dev/null >build.log 2>&1
	cd $(JMX4PERL_BUILD_DIR) && ./Build
	$(TOUCH) $@

$(JMX4PERL_INSTALL): $(JMX4PERL_BUILD)
	rm -rf $(DESTDIR)$(OMD_ROOT)/skel/etc/jmx4perl
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/skel/etc/jmx4perl
	rsync -a $(JMX4PERL_BUILD_DIR)/config $(DESTDIR)$(OMD_ROOT)/skel/etc/jmx4perl/
	chmod 644 $(DESTDIR)$(OMD_ROOT)/skel/etc/jmx4perl/config/*.cfg
	cp -p $(JMX4PERL_BUILD_DIR)/blib/script/jmx4perl $(DESTDIR)$(OMD_ROOT)/bin/
	cp -p $(JMX4PERL_BUILD_DIR)/blib/script/j4psh $(DESTDIR)$(OMD_ROOT)/bin/
	cp -p $(JMX4PERL_BUILD_DIR)/blib/script/jolokia $(DESTDIR)$(OMD_ROOT)/bin/
	cp -p $(JMX4PERL_BUILD_DIR)/blib/script/check_jmx4perl $(DESTDIR)$(OMD_ROOT)/lib/nagios/plugins/
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib/perl5/lib/perl5
	rsync -a $(JMX4PERL_BUILD_DIR)/blib/lib/ $(DESTDIR)$(OMD_ROOT)/lib/perl5/lib/perl5
	rsync -a $(JMX4PERL_BUILD_DIR)/blib/bindoc/ $(DESTDIR)$(OMD_ROOT)/share/man/man1
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/doc/jmx4perl
	install -m 644 $(PACKAGE_DIR)/$(JMX4PERL)/README $(DESTDIR)$(OMD_ROOT)/share/doc/jmx4perl
# Jolokia Agents
	rm -rf $(DESTDIR)$(OMD_ROOT)/share/jmx4perl
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/jmx4perl/jolokia-$(JOLOKIA_VERSION)
	rsync -a $(PACKAGE_DIR)/$(JMX4PERL)/jolokia-agents/$(JOLOKIA_VERSION)/ $(DESTDIR)$(OMD_ROOT)/share/jmx4perl/jolokia-$(JOLOKIA_VERSION)/
	chmod 644 $(DESTDIR)$(OMD_ROOT)/share/jmx4perl/jolokia-$(JOLOKIA_VERSION)/*
	$(TOUCH) $@
