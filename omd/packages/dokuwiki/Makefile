include ../../Makefile.omd

NAME = dokuwiki
VERSION = 2016-06-26a
DIR = $(NAME)

.PHONY: skel

build:
	tar xzf $(NAME)-$(VERSION).tgz
	tar xzf template-arctictut.tgz -C $(DIR)/lib/tpl/
	ln -sf ../../../images/fileicons/pdf.png $(DIR)/lib/tpl/arctictut/images/tool-pdf.png
	tar xzf template-vector.tgz -C $(DIR)/lib/tpl/
	
	# ./indexmenu/images/bw.png needs to be excluded because the images in this directory
	# are licensed with "Copyright: Creative Commons Attribution Non-Commercial No Derivatives".
	for p in plugins/*.tgz ; do \
		echo "add plugin $$p..." ; \
		tar xzf $$p --exclude 'indexmenu/images/bw.png' -C $(DIR)/lib/plugins ; \
	done
	
	for p in patches/*.patch ; do \
		echo "applying $$p..." ; \
		patch -p1 -b -d $(DIR) < $$p ; \
	done
	find $(DIR)/ -name \*.orig -exec rm {} \;

install:
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/dokuwiki
	cp preload.php $(DIR)/inc/
	cp -r authmultisite $(DIR)/lib/plugins/
#	touch $(DIR)/conf $(DIR)/data
#	rm -r $(DIR)/conf $(DIR)/data
	cp -r $(DIR) $(DESTDIR)$(OMD_ROOT)/share/dokuwiki/htdocs
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/doc/dokuwiki
	install -m 644 $(DIR)/README $(DESTDIR)$(OMD_ROOT)/share/doc/dokuwiki
	install -m 644 $(DIR)/COPYING $(DESTDIR)$(OMD_ROOT)/share/doc/dokuwiki
	install -m 644 $(DIR)/VERSION $(DESTDIR)$(OMD_ROOT)/share/doc/dokuwiki

#install:
#	$(MAKE) DESTDIR=$(DESTDIR) -C $(DIR) -j 1 install
#	# fix path for plugin
#	[ -d $(DESTDIR)$(OMD_ROOT)/lib/nagios/plugins ] || mkdir -p $(DESTDIR)$(OMD_ROOT)/lib/nagios/plugins
#	mv $(DESTDIR)$(OMD_ROOT)/bin/check_gearman $(DESTDIR)$(OMD_ROOT)/lib/nagios/plugins/
#	rm -rf $(DESTDIR)$(OMD_ROOT)/share/mod_gearman/*.conf
#	rm -f $(DESTDIR)$(OMD_ROOT)/lib/mod_gearman/mod_gearman.so
#	rm -rf $(DESTDIR)$(OMD_ROOT)/etc
#	rm -rf $(DESTDIR)$(OMD_ROOT)/var

skel:
	mkdir -p $(SKEL)/etc/dokuwiki
	mkdir -p $(SKEL)/var/dokuwiki/lib/plugins
	cp $(DIR)/conf/*.conf				$(SKEL)/etc/dokuwiki/.
	cp $(DIR)/conf/*.php$				$(SKEL)/etc/dokuwiki/.
	cp $(DIR)/conf/acl.auth.php.dist	$(SKEL)/etc/dokuwiki/acl.auth.php
	cp $(DIR)/conf/mysql.conf.php.example $(SKEL)/etc/dokuwiki/mysql.conf.php.example

	for p in patches/*.skel_patch ; do \
	    echo "applying $$p..." ; \
	    ( cd $(SKEL) ; patch -p1 ) < $$p || exit 1; \
	done

	cd $(SKEL)/var/dokuwiki/lib/plugins/ ; \
	for i in `ls -1 $(DESTDIR)$(OMD_ROOT)/share/dokuwiki/htdocs/lib/plugins/` ; do \
	    ln -s ../../../../share/dokuwiki/htdocs/lib/plugins/$$i . ; \
	done

clean:
	# Remove files created by build/install
	rm -rf $(DIR)
