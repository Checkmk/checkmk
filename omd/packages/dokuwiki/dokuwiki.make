DOKUWIKI := dokuwiki
DOKUWIKI_VERS := 2018-04-22b
DOKUWIKI_DIR := $(DOKUWIKI)-$(DOKUWIKI_VERS)

DOKUWIKI_BUILD := $(BUILD_HELPER_DIR)/$(DOKUWIKI_DIR)-build
DOKUWIKI_INSTALL := $(BUILD_HELPER_DIR)/$(DOKUWIKI_DIR)-install
DOKUWIKI_UNPACK := $(BUILD_HELPER_DIR)/$(DOKUWIKI_DIR)-unpack
DOKUWIKI_UNPACK_ADDITIONAL := $(BUILD_HELPER_DIR)/$(DOKUWIKI_DIR)-unpack-additional
DOKUWIKI_PATCHING := $(BUILD_HELPER_DIR)/$(DOKUWIKI_DIR)-patching

#DOKUWIKI_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(DOKUWIKI_DIR)
DOKUWIKI_BUILD_DIR := $(PACKAGE_BUILD_DIR)/$(DOKUWIKI_DIR)
#DOKUWIKI_WORK_DIR := $(PACKAGE_WORK_DIR)/$(DOKUWIKI_DIR)

$(DOKUWIKI_UNPACK_ADDITIONAL): $(DOKUWIKI_UNPACK)
	$(TAR_GZ) $(PACKAGE_DIR)/$(DOKUWIKI)/template-arctictut.tgz -C $(DOKUWIKI_BUILD_DIR)/lib/tpl/
	$(LN) -sf $(DOKUWIKI_BUILD_DIR)/lib/images/fileicons/pdf.png $(DOKUWIKI_BUILD_DIR)/lib/tpl/arctictut/images/tool-pdf.png
	$(TAR_GZ) $(PACKAGE_DIR)/$(DOKUWIKI)/template-vector.tgz -C $(DOKUWIKI_BUILD_DIR)/lib/tpl/
	
	# ./indexmenu/images/bw.png needs to be excluded because the images in this directory
	# are licensed with "Copyright: Creative Commons Attribution Non-Commercial No Derivatives".
	for p in $(PACKAGE_DIR)/$(DOKUWIKI)/plugins/*.tgz ; do \
		echo "add plugin $$p..." ; \
		$(TAR_GZ) $$p --exclude 'indexmenu/images/bw.png' -C $(DOKUWIKI_BUILD_DIR)/lib/plugins ; \
	done
	$(TOUCH) $@

# Additional archives have to be unpacked, before the patching works
$(DOKUWIKI_PATCHING): $(DOKUWIKI_UNPACK_ADDITIONAL)

$(DOKUWIKI_BUILD): $(DOKUWIKI_PATCHING)
	$(FIND) $(DOKUWIKI_BUILD_DIR)/ -name \*.orig -exec rm {} \;
	$(TOUCH) $@

$(DOKUWIKI_INSTALL): $(DOKUWIKI_BUILD)
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/dokuwiki
	cp $(PACKAGE_DIR)/$(DOKUWIKI)/preload.php $(DOKUWIKI_BUILD_DIR)/inc/
	cp -r $(PACKAGE_DIR)/$(DOKUWIKI)/authmultisite $(DOKUWIKI_BUILD_DIR)/lib/plugins/
	cp -r $(DOKUWIKI_BUILD_DIR) $(DESTDIR)$(OMD_ROOT)/share/dokuwiki/htdocs
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/doc/dokuwiki
	install -m 644 $(DOKUWIKI_BUILD_DIR)/README $(DESTDIR)$(OMD_ROOT)/share/doc/dokuwiki
	install -m 644 $(DOKUWIKI_BUILD_DIR)/COPYING $(DESTDIR)$(OMD_ROOT)/share/doc/dokuwiki
	install -m 644 $(DOKUWIKI_BUILD_DIR)/VERSION $(DESTDIR)$(OMD_ROOT)/share/doc/dokuwiki
	install -m 755 $(PACKAGE_DIR)/$(DOKUWIKI)/DOKUWIKI_AUTH $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks/

	$(MKDIR) $(SKEL)/etc/dokuwiki
	$(MKDIR) $(SKEL)/var/dokuwiki/lib/plugins
	cp $(DOKUWIKI_BUILD_DIR)/conf/*.conf				$(SKEL)/etc/dokuwiki/.
	cp $(DOKUWIKI_BUILD_DIR)/conf/*.php$				$(SKEL)/etc/dokuwiki/.
	cp $(DOKUWIKI_BUILD_DIR)/conf/acl.auth.php.dist	$(SKEL)/etc/dokuwiki/acl.auth.php
	cp $(DOKUWIKI_BUILD_DIR)/conf/mysql.conf.php.example $(SKEL)/etc/dokuwiki/mysql.conf.php.example

	for p in $(PACKAGE_DIR)/$(DOKUWIKI)/patches/*.skel_patch ; do \
	    echo "applying $$p..." ; \
	    ( cd $(SKEL) ; patch -p1 ) < $$p || exit 1; \
	done

	cd $(SKEL)/var/dokuwiki/lib/plugins/ ; \
	for i in `ls -1 $(DESTDIR)$(OMD_ROOT)/share/dokuwiki/htdocs/lib/plugins/` ; do \
	    $(LN) -sf ../../../../share/dokuwiki/htdocs/lib/plugins/$$i . ; \
	done
	$(TOUCH) $@
