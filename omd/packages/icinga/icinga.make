ICINGA := icinga
ICINGA_VERS := 1.13.3
ICINGA_DIR := $(ICINGA)-$(ICINGA_VERS)

ICINGA_BUILD := $(BUILD_HELPER_DIR)/$(ICINGA_DIR)-build
ICINGA_INSTALL := $(BUILD_HELPER_DIR)/$(ICINGA_DIR)-install
ICINGA_PATCHING := $(BUILD_HELPER_DIR)/$(ICINGA_DIR)-patching

.PHONY: $(ICINGA) $(ICINGA)-install $(ICINGA)-skel

$(ICINGA): $(ICINGA_BUILD)

$(ICINGA)-install: $(ICINGA_INSTALL)

# Configure options for Icinga. Since we want to compile
# as non-root, we use our own user and group for compiling.
# All files will be packaged as user 'root' later anyway.
ICINGA_CONFIGUREOPTS := \
    --sbindir=$(OMD_ROOT)/lib/icinga/cgi-bin \
    --bindir=$(OMD_ROOT)/bin \
    --datarootdir=$(OMD_ROOT)/share/icinga/htdocs \
    --with-icinga-user=$$(id -un) \
    --with-icinga-group=$$(id -gn) \
    --with-web-user=$$(id -un) \
    --with-web-group=$$(id -gn) \
    --with-perlcache \
    --enable-embedded-perl \
    --with-cgiurl="./cgi-bin" \
    --with-htmurl="." \
    --enable-idoutils=no \

$(ICINGA_BUILD): $(ICINGA_PATCHING)
	cd $(ICINGA_DIR) ; ./configure $(ICINGA_CONFIGUREOPTS)
	$(MAKE) -C $(ICINGA_DIR) all
	$(MAKE) -C $(ICINGA_DIR)/module/idoutils/src idomod.so
	$(TOUCH) $@

$(ICINGA_INSTALL): $(ICINGA_BUILD)
	$(MAKE) DESTDIR=$(DESTDIR) -C $(ICINGA_DIR) install-base install-cgis install-html
	$(RM) $(DESTDIR)$(OMD_ROOT)/share/icinga/htdocs/config.php.inc

	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib/icinga
	install -m 664 $(ICINGA_DIR)/p1.pl $(DESTDIR)$(OMD_ROOT)/lib/icinga
	install -m 664 $(ICINGA_DIR)/module/idoutils/src/idomod.so $(DESTDIR)$(OMD_ROOT)/lib/icinga

	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/icinga/htdocs/ssi
	install -m 755 $(PACKAGE_DIR)/$(ICINGA)/ssi-wrapper.pl $(DESTDIR)$(OMD_ROOT)/share/icinga/htdocs/ssi

	for f in common avail cmd config extinfo histogram history notifications outages showlog status statusmap statuswml statuswrl summary tac trends ; do \
		$(LN) -sfn ssi-wrapper.pl $(DESTDIR)$(OMD_ROOT)/share/icinga/htdocs/ssi/$$f-header.ssi ; \
		$(LN) -sfn ssi-wrapper.pl $(DESTDIR)$(OMD_ROOT)/share/icinga/htdocs/ssi/$$f-footer.ssi ; \
	done

	# Copy package documentations to have these information in the binary packages
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/doc/$(ICINGA)
	for file in README THANKS LEGAL LICENSE ; do \
	   install -m 644 $(ICINGA_DIR)/$$file $(DESTDIR)$(OMD_ROOT)/share/doc/$(ICINGA); \
	done

	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/bin
	install -m 755 $(PACKAGE_DIR)/$(ICINGA)/merge-icinga-config $(DESTDIR)$(OMD_ROOT)/bin

	# remove empty folders
	$(RM) -r $(DESTDIR)/usr
	$(TOUCH) $@
  
icinga-skel:

icinga-clean:
	$(RM) -r $(ICINGA_DIR)
