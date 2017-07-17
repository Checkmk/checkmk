include ../../Makefile.omd

NAME = icinga
VERSION = 1.13.3
DIR = $(NAME)-$(VERSION)

# Configure options for Icinga. Since we want to compile
# as non-root, we use our own user and group for compiling.
# All files will be packaged as user 'root' later anyway.
CONFIGUREOPTS = \
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

build:
	tar xzf $(DIR).tar.gz

	set -e ; for p in patches/*.dif ; do \
	        echo "applying $$p..." ; \
		patch -p1 -b -d $(DIR) < $$p ; \
        done

	cd $(DIR) ; ./configure $(CONFIGUREOPTS)
	$(MAKE) -C $(DIR) all


	$(MAKE) -C $(DIR)/module/idoutils/src idomod.so


install:
	$(MAKE) DESTDIR=$(DESTDIR) -C $(DIR) install-base install-cgis install-html
	rm -f $(DESTDIR)$(OMD_ROOT)/share/icinga/htdocs/config.php.inc

	mkdir -p $(DESTDIR)$(OMD_ROOT)/lib/icinga
	install -m 664 $(DIR)/p1.pl $(DESTDIR)$(OMD_ROOT)/lib/icinga
	install -m 664 $(DIR)/module/idoutils/src/idomod.so $(DESTDIR)$(OMD_ROOT)/lib/icinga

	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/icinga/htdocs/ssi
	install -m 755 ssi-wrapper.pl $(DESTDIR)$(OMD_ROOT)/share/icinga/htdocs/ssi

	for f in common avail cmd config extinfo histogram history notifications outages showlog status statusmap statuswml statuswrl summary tac trends ; do \
		ln -sfn ssi-wrapper.pl $(DESTDIR)$(OMD_ROOT)/share/icinga/htdocs/ssi/$$f-header.ssi ; \
		ln -sfn ssi-wrapper.pl $(DESTDIR)$(OMD_ROOT)/share/icinga/htdocs/ssi/$$f-footer.ssi ; \
	done

	# Copy package documentations to have these information in the binary packages
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/doc/$(NAME)
	for file in README THANKS LEGAL LICENSE ; do \
	   install -m 644 $(DIR)/$$file $(DESTDIR)$(OMD_ROOT)/share/doc/$(NAME); \
	done

	mkdir -p $(DESTDIR)$(OMD_ROOT)/bin
	install -m 755 merge-icinga-config $(DESTDIR)$(OMD_ROOT)/bin

	# remove empty folders
	rm -rf $(DESTDIR)/usr
  
clean:
	rm -rf $(DIR)
