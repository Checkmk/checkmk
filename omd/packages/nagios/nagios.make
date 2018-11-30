NAGIOS := nagios
NAGIOS_VERS := 3.5.1
NAGIOS_DIR := $(NAGIOS)-$(NAGIOS_VERS)

NAGIOS_BUILD := $(BUILD_HELPER_DIR)/$(NAGIOS_DIR)-build
NAGIOS_INSTALL := $(BUILD_HELPER_DIR)/$(NAGIOS_DIR)-install
NAGIOS_PATCHING := $(BUILD_HELPER_DIR)/$(NAGIOS_DIR)-patching

.PHONY: $(NAGIOS) $(NAGIOS)-install $(NAGIOS)-skel $(NAGIOS)-build

$(NAGIOS): $(NAGIOS_BUILD)

$(NAGIOS)-install: $(NAGIOS_INSTALL)

# Configure options for Nagios. Since we want to compile
# as non-root, we use our own user and group for compiling.
# All files will be packaged as user 'root' later anyway.
NAGIOS_CONFIGUREOPTS := \
    --sbindir=$(OMD_ROOT)/lib/nagios/cgi-bin \
    --bindir=$(OMD_ROOT)/bin \
    --datadir=$(OMD_ROOT)/share/nagios/htdocs \
    --with-nagios-user=$$(id -un) \
    --with-nagios-group=$$(id -gn) \
    --with-perlcache \
    --enable-embedded-perl \

$(NAGIOS_BUILD): $(NAGIOS_PATCHING)
	find $(NAGIOS_DIR)/ -name \*.orig -exec rm {} \;
	cd $(NAGIOS_DIR) ; ./configure $(NAGIOS_CONFIGUREOPTS)
	$(MAKE) -C $(NAGIOS_DIR) all
	$(TOUCH) $@

$(NAGIOS_INSTALL): $(NAGIOS_BUILD)
	$(MAKE) DESTDIR=$(DESTDIR) -C $(NAGIOS_DIR) install-base
	
	install -m 664 $(NAGIOS_DIR)/p1.pl $(DESTDIR)$(OMD_ROOT)/lib/nagios
	
	# Copy package documentations to have these information in the binary packages
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/doc/$(NAGIOS)
	for file in README THANKS LEGAL LICENSE ; do \
	   install -m 644 $(NAGIOS_DIR)/$$file $(DESTDIR)$(OMD_ROOT)/share/doc/$(NAGIOS); \
	done
	
	install -m 755 $(PACKAGE_DIR)/$(NAGIOS)/merge-nagios-config $(DESTDIR)$(OMD_ROOT)/bin
	
	# Install the diskspace cleanup plugin
	install -m 644 $(PACKAGE_DIR)/$(NAGIOS)/diskspace $(DESTDIR)$(OMD_ROOT)/share/diskspace/nagios
	install -m 755 $(PACKAGE_DIR)/$(NAGIOS)/NAGIOS_THEME $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks/
	$(TOUCH) $@
  
$(NAGIOS)-skel:

$(NAGIOS)-clean:
	rm -rf $(NAGIOS_DIR) $(BUILD_HELPER_DIR)/$(NAGIOS)*

$(NAGIOS)-testpatches:
	@rm -rf $(NAGIOS_DIR)
	@tar xzf $(NAGIOS_DIR).tar.gz
	@set -e ; for p in patches/*.dif ; do \
	    rm -rf $(NAGIOS_DIR).orig; \
	    cp -rp $(NAGIOS_DIR) $(NAGIOS_DIR).orig; \
	    ( cd $(NAGIOS_DIR) ; patch -sNt -p1 -r - ) < $$p > /dev/null; \
	    find $(NAGIOS_DIR) -name \*.orig -exec rm {} \;; \
	    [ $$(diff -wr $(NAGIOS_DIR).orig/. $(NAGIOS_DIR)/. | wc -l) = 0 ] && echo "-> patch $$p did not change anything (already applied or broken)" || echo -n ""; \
	done
	@rm -rf $(NAGIOS_DIR).orig
	@echo "all patches tested"
