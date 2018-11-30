DOKUWIKI = dokuwiki
DOKUWIKI_VERS = 2016-06-26e
DOKUWIKI_DIR = $(DOKUWIKI)-$(DOKUWIKI_VERS)

DOKUWIKI_BUILD := $(BUILD_HELPER_DIR)/$(DOKUWIKI_DIR)-build
DOKUWIKI_INSTALL := $(BUILD_HELPER_DIR)/$(DOKUWIKI_DIR)-install
DOKUWIKI_UNPACK := $(BUILD_HELPER_DIR)/$(DOKUWIKI_DIR)-unpack
DOKUWIKI_UNPACK_ADDITIONAL := $(BUILD_HELPER_DIR)/$(DOKUWIKI_DIR)-unpack-additional
DOKUWIKI_PATCHING := $(BUILD_HELPER_DIR)/$(DOKUWIKI_DIR)-patching

.PHONY: $(DOKUWIKI) $(DOKUWIKI)-install $(DOKUWIKI)-skel $(DOKUWIKI)-build

$(DOKUWIKI): $(DOKUWIKI_BUILD)

$(DOKUWIKI)-install: $(DOKUWIKI_INSTALL)

$(DOKUWIKI_UNPACK_ADDITIONAL): $(DOKUWIKI_UNPACK) 
	$(TAR_GZ) $(PACKAGE_DIR)/$(DOKUWIKI)/template-arctictut.tgz -C $(DOKUWIKI_DIR)/lib/tpl/
	$(LN) -sf $(DOKUWIKI_DIR)/lib/images/fileicons/pdf.png $(DOKUWIKI_DIR)/lib/tpl/arctictut/images/tool-pdf.png
	$(TAR_GZ) $(PACKAGE_DIR)/$(DOKUWIKI)/template-vector.tgz -C $(DOKUWIKI_DIR)/lib/tpl/
	
	# ./indexmenu/images/bw.png needs to be excluded because the images in this directory
	# are licensed with "Copyright: Creative Commons Attribution Non-Commercial No Derivatives".
	for p in $(PACKAGE_DIR)/$(DOKUWIKI)/plugins/*.tgz ; do \
		echo "add plugin $$p..." ; \
		$(TAR_GZ) $$p --exclude 'indexmenu/images/bw.png' -C $(DOKUWIKI_DIR)/lib/plugins ; \
	done
	$(TOUCH) $@

# Additional archives have to be unpacked, before the patching works
$(DOKUWIKI_PATCHING): $(DOKUWIKI_UNPACK_ADDITIONAL)

$(DOKUWIKI_BUILD): $(DOKUWIKI_PATCHING)
	$(FIND) $(DOKUWIKI_DIR)/ -name \*.orig -exec rm {} \;
	$(TOUCH) $@

$(DOKUWIKI_INSTALL): $(DOKUWIKI_BUILD)
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/dokuwiki
	cp $(PACKAGE_DIR)/$(DOKUWIKI)/preload.php $(DOKUWIKI_DIR)/inc/
	cp -r $(PACKAGE_DIR)/$(DOKUWIKI)/authmultisite $(DOKUWIKI_DIR)/lib/plugins/
#	touch $(DOKUWIKI_DIR)/conf $(DOKUWIKI_DIR)/data
#	rm -r $(DOKUWIKI_DIR)/conf $(DOKUWIKI_DIR)/data
	cp -r $(DOKUWIKI_DIR) $(DESTDIR)$(OMD_ROOT)/share/dokuwiki/htdocs
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/doc/dokuwiki
	install -m 644 $(DOKUWIKI_DIR)/README $(DESTDIR)$(OMD_ROOT)/share/doc/dokuwiki
	install -m 644 $(DOKUWIKI_DIR)/COPYING $(DESTDIR)$(OMD_ROOT)/share/doc/dokuwiki
	install -m 644 $(DOKUWIKI_DIR)/VERSION $(DESTDIR)$(OMD_ROOT)/share/doc/dokuwiki
	install -m 755 $(PACKAGE_DIR)/$(DOKUWIKI)/DOKUWIKI_AUTH $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks/
	$(TOUCH) $@

#install:
#	$(MAKE) DESTDIR=$(DESTDIR) -C $(DOKUWIKI_DIR) -j 1 install
#	# fix path for plugin
#	mv $(DESTDIR)$(OMD_ROOT)/bin/check_gearman $(DESTDIR)$(OMD_ROOT)/lib/nagios/plugins/
#	rm -rf $(DESTDIR)$(OMD_ROOT)/share/mod_gearman/*.conf
#	rm -f $(DESTDIR)$(OMD_ROOT)/lib/mod_gearman/mod_gearman.so
#	rm -rf $(DESTDIR)$(OMD_ROOT)/etc
#	rm -rf $(DESTDIR)$(OMD_ROOT)/var

$(DOKUWIKI)-skel: $(DOKUWIKI_INSTALL)
	$(MKDIR) $(SKEL)/etc/dokuwiki
	$(MKDIR) $(SKEL)/var/dokuwiki/lib/plugins
	cp $(DOKUWIKI_DIR)/conf/*.conf				$(SKEL)/etc/dokuwiki/.
	cp $(DOKUWIKI_DIR)/conf/*.php$				$(SKEL)/etc/dokuwiki/.
	cp $(DOKUWIKI_DIR)/conf/acl.auth.php.dist	$(SKEL)/etc/dokuwiki/acl.auth.php
	cp $(DOKUWIKI_DIR)/conf/mysql.conf.php.example $(SKEL)/etc/dokuwiki/mysql.conf.php.example

	for p in $(PACKAGE_DIR)/$(DOKUWIKI)/patches/*.skel_patch ; do \
	    echo "applying $$p..." ; \
	    ( cd $(SKEL) ; patch -p1 ) < $$p || exit 1; \
	done

	cd $(SKEL)/var/dokuwiki/lib/plugins/ ; \
	for i in `ls -1 $(DESTDIR)$(OMD_ROOT)/share/dokuwiki/htdocs/lib/plugins/` ; do \
	    $(LN) -s ../../../../share/dokuwiki/htdocs/lib/plugins/$$i . ; \
	done

$(DOKUWIKI)-clean:
	# Remove files created by build/install
	$(RM) -r $(DOKUWIKI_DIR) $(BUILD_HELPER_DIR)/$(DOKUWIKI)*
