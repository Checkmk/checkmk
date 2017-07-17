include ../../Makefile.omd

NAME = nagios
VERSION = 3.5.0
DIR = $(NAME)-$(VERSION)

# Configure options for Nagios. Since we want to compile
# as non-root, we use our own user and group for compiling.
# All files will be packaged as user 'root' later anyway.
CONFIGUREOPTS = \
    --sbindir=$(OMD_ROOT)/lib/nagios/cgi-bin \
    --bindir=$(OMD_ROOT)/bin \
    --datadir=$(OMD_ROOT)/share/nagios/htdocs \
    --with-nagios-user=$$(id -un) \
    --with-nagios-group=$$(id -gn) \
    --with-perlcache \
    --enable-embedded-perl \

build:
	$(MAKE) prep
	$(MAKE) compile

prep:
	$(MAKE) unpack
	$(MAKE) patch

compile:
	cd $(DIR) ; ./configure $(CONFIGUREOPTS)
	$(MAKE) -C $(DIR) all

unpack:
	rm -rf $(DIR)
	tar xzf $(DIR).tar.gz
	mv nagios $(DIR)


patch:
	set -e ; for p in patches/*.dif ; do \
	    echo "applying $$p..." ; \
	    patch -p1 -b -d $(DIR) < $$p ; \
	done
	find $(DIR)/ -name \*.orig -exec rm {} \;



install:
	$(MAKE) DESTDIR=$(DESTDIR) -C $(DIR) install-base install-cgis install-html install-classicui
	rm -f $(DESTDIR)$(OMD_ROOT)/share/nagios/htdocs/config.php.inc
	
	# Install Themes
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/nagios/htdocs/themes/classicui 
	cp -a $(DESTDIR)$(OMD_ROOT)/share/nagios/htdocs/stylesheets $(DESTDIR)$(OMD_ROOT)/share/nagios/htdocs/themes/classicui/
	cp -a $(DESTDIR)$(OMD_ROOT)/share/nagios/htdocs/images      $(DESTDIR)$(OMD_ROOT)/share/nagios/htdocs/themes/classicui/
	$(MAKE) DESTDIR=$(DESTDIR) -C $(DIR) install-exfoliation
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/nagios/htdocs/themes/exfoliation 
	cp -a $(DESTDIR)$(OMD_ROOT)/share/nagios/htdocs/stylesheets $(DESTDIR)$(OMD_ROOT)/share/nagios/htdocs/themes/exfoliation/
	cp -a $(DESTDIR)$(OMD_ROOT)/share/nagios/htdocs/images      $(DESTDIR)$(OMD_ROOT)/share/nagios/htdocs/themes/exfoliation/
	# remove original files
	rm -rf $(DESTDIR)$(OMD_ROOT)/share/nagios/htdocs/stylesheets
	rm -rf $(DESTDIR)$(OMD_ROOT)/share/nagios/htdocs/images
	# Link ClassicUI
	cd $(DESTDIR)$(OMD_ROOT)/share/nagios/htdocs; rm -rf styleshets; ln -sfn themes/classicui/stylesheets
	cd $(DESTDIR)$(OMD_ROOT)/share/nagios/htdocs; rm -rf images; ln -sfn themes/classicui/images
	
	mkdir -p $(DESTDIR)$(OMD_ROOT)/lib/nagios
	install -m 664 $(DIR)/p1.pl $(DESTDIR)$(OMD_ROOT)/lib/nagios
	
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/nagios/htdocs/ssi
	install -m 755 ssi-wrapper.pl $(DESTDIR)$(OMD_ROOT)/share/nagios/htdocs/ssi
	
	for f in common avail cmd config extinfo histogram history notifications outages showlog status statusmap statuswml statuswrl summary tac trends ; do \
		ln -sfn ssi-wrapper.pl $(DESTDIR)$(OMD_ROOT)/share/nagios/htdocs/ssi/$$f-header.ssi ; \
		ln -sfn ssi-wrapper.pl $(DESTDIR)$(OMD_ROOT)/share/nagios/htdocs/ssi/$$f-footer.ssi ; \
	done
	
	# Copy package documentations to have these information in the binary packages
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/doc/$(NAME)
	for file in README THANKS LEGAL LICENSE ; do \
	   install -m 644 $(DIR)/$$file $(DESTDIR)$(OMD_ROOT)/share/doc/$(NAME); \
	done
	
	mkdir -p $(DESTDIR)$(OMD_ROOT)/bin
	install -m 755 merge-nagios-config $(DESTDIR)$(OMD_ROOT)/bin
	
	# Install the diskspace cleanup plugin
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/diskspace
	install -m 644 diskspace $(DESTDIR)$(OMD_ROOT)/share/diskspace/nagios
  
clean:
	rm -rf $(DIR)

testpatches:
	@rm -rf $(DIR)
	@tar xzf $(DIR).tar.gz
	@set -e ; for p in patches/*.dif ; do \
	    rm -rf $(DIR).orig; \
	    cp -rp $(DIR) $(DIR).orig; \
	    ( cd $(DIR) ; patch -sNt -p1 -r - ) < $$p > /dev/null; \
	    find $(DIR) -name \*.orig -exec rm {} \;; \
	    [ $$(diff -wr $(DIR).orig/. $(DIR)/. | wc -l) = 0 ] && echo "-> patch $$p did not change anything (already applied or broken)" || echo -n ""; \
	done
	@rm -rf $(DIR).orig
	@echo "all patches tested"
