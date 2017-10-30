include ../../Makefile.omd

NAME = nagvis
VERSION = 1.9.4
DIR = $(NAME)-$(VERSION)

.PHONY: skel

build:
	tar xzf $(DIR).tar.gz
	for p in patches/*.patch; do \
		echo "applying $$p..." ; \
		patch -p1 -b -d $(DIR) < $$p ; \
        done

install:
	cd $(DIR) ; ./install.sh -q -F -c y -a n \
	 -u $$(id -un) \
	 -g $$(id -gn) \
	 -w $(DESTDIR)$(OMD_ROOT)/etc/apache \
	 -W /WILL_BE_REPLACED/nagvis \
	 -b $(DESTDIR)/usr/bin \
	 -p $(DESTDIR)$(OMD_ROOT)/share/nagvis
	
	# Relocate the NagVis shared directory to have the same path as all the other packages
	test -d $(DESTDIR)$(OMD_ROOT)/share/nagvis/share && \
	  mv $(DESTDIR)$(OMD_ROOT)/share/nagvis/share $(DESTDIR)$(OMD_ROOT)/share/nagvis/htdocs
	
	mkdir -p $(DESTDIR)$(OMD_ROOT)/skel/var/nagvis/profiles
	
	# Move package documentations to have these files in the binary packages
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/doc/$(NAME)
	for file in COPYING README ; do \
	  mv $(DESTDIR)$(OMD_ROOT)/share/nagvis/$$file $(DESTDIR)$(OMD_ROOT)/share/doc/$(NAME); \
	done
	
	# Take the sample main configuration file from source package and overwrite the one 
	# installed by the installer.
	mkdir -p $(DESTDIR)$(OMD_ROOT)/skel/etc/nagvis
	cp $(DIR)/etc/nagvis.ini.php-sample $(DESTDIR)$(OMD_ROOT)/skel/etc/nagvis/nagvis.ini.php
	
	# Move demo config files
	mkdir -p $(DESTDIR)$(OMD_ROOT)/skel/etc/nagvis/conf.d
	mkdir -p $(DESTDIR)$(OMD_ROOT)/skel/etc/nagvis/maps
	mkdir -p $(DESTDIR)$(OMD_ROOT)/skel/etc/nagvis/geomap
	rm $(DESTDIR)$(OMD_ROOT)/share/nagvis/etc/maps/*.cfg
	mv $(DESTDIR)$(OMD_ROOT)/share/nagvis/etc/conf.d/*.ini.php $(DESTDIR)$(OMD_ROOT)/skel/etc/nagvis/conf.d
	mv $(DESTDIR)$(OMD_ROOT)/share/nagvis/etc/geomap/demo-*.csv $(DESTDIR)$(OMD_ROOT)/skel/etc/nagvis/geomap
	
	# Delete files/directories we do not want to pack
	rm -rf $(DESTDIR)$(OMD_ROOT)/share/nagvis/var
	rm -rf $(DESTDIR)$(OMD_ROOT)/share/nagvis/etc

clean:
	rm -rf $(NAME)-*.*.[0-9] $(NAME)-*.*-nightly
