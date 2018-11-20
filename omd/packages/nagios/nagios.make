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

$(NAGIOS_INSTALL):
	$(MAKE) DESTDIR=$(DESTDIR) -C $(NAGIOS_DIR) install-base install-cgis install-html install-classicui
	rm -f $(DESTDIR)$(OMD_ROOT)/share/nagios/htdocs/config.php.inc
	
	# Install Themes
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/nagios/htdocs/themes/classicui 
	cp -af $(DESTDIR)$(OMD_ROOT)/share/nagios/htdocs/stylesheets $(DESTDIR)$(OMD_ROOT)/share/nagios/htdocs/themes/classicui/
	cp -af $(DESTDIR)$(OMD_ROOT)/share/nagios/htdocs/images      $(DESTDIR)$(OMD_ROOT)/share/nagios/htdocs/themes/classicui/
	$(MAKE) DESTDIR=$(DESTDIR) -C $(NAGIOS_DIR) install-exfoliation
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/nagios/htdocs/themes/exfoliation 
	cp -af $(DESTDIR)$(OMD_ROOT)/share/nagios/htdocs/stylesheets $(DESTDIR)$(OMD_ROOT)/share/nagios/htdocs/themes/exfoliation/
	cp -af $(DESTDIR)$(OMD_ROOT)/share/nagios/htdocs/images $(DESTDIR)$(OMD_ROOT)/share/nagios/htdocs/themes/exfoliation/
	# remove original files
	rm -rf $(DESTDIR)$(OMD_ROOT)/share/nagios/htdocs/stylesheets
	rm -rf $(DESTDIR)$(OMD_ROOT)/share/nagios/htdocs/images
	# Link ClassicUI
	cd $(DESTDIR)$(OMD_ROOT)/share/nagios/htdocs; rm -rf styleshets; ln -sfn themes/classicui/stylesheets
	cd $(DESTDIR)$(OMD_ROOT)/share/nagios/htdocs; rm -rf images; ln -sfn themes/classicui/images
	
	mkdir -p $(DESTDIR)$(OMD_ROOT)/lib/nagios
	install -m 664 $(NAGIOS_DIR)/p1.pl $(DESTDIR)$(OMD_ROOT)/lib/nagios
	
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/nagios/htdocs/ssi
	install -m 755 $(PACKAGE_DIR)/$(NAGIOS)/ssi-wrapper.pl $(DESTDIR)$(OMD_ROOT)/share/nagios/htdocs/ssi
	
	for f in common avail cmd config extinfo histogram history notifications outages showlog status statusmap statuswml statuswrl summary tac trends ; do \
		ln -sfn ssi-wrapper.pl $(DESTDIR)$(OMD_ROOT)/share/nagios/htdocs/ssi/$$f-header.ssi ; \
		ln -sfn ssi-wrapper.pl $(DESTDIR)$(OMD_ROOT)/share/nagios/htdocs/ssi/$$f-footer.ssi ; \
	done
	
	# Copy package documentations to have these information in the binary packages
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/doc/$(NAGIOS)
	for file in README THANKS LEGAL LICENSE ; do \
	   install -m 644 $(NAGIOS_DIR)/$$file $(DESTDIR)$(OMD_ROOT)/share/doc/$(NAGIOS); \
	done
	
	mkdir -p $(DESTDIR)$(OMD_ROOT)/bin
	install -m 755 $(PACKAGE_DIR)/$(NAGIOS)/merge-nagios-config $(DESTDIR)$(OMD_ROOT)/bin
	
	# Install the diskspace cleanup plugin
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/diskspace
	install -m 644 $(PACKAGE_DIR)/$(NAGIOS)/diskspace $(DESTDIR)$(OMD_ROOT)/share/diskspace/nagios
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
