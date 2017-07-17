include ../../Makefile.omd

NAME     = jmx4perl
VERSION  = 1.11
JOLOKIA_VERSION = 1.2.3
DIR      = $(NAME)-$(VERSION)

.PHONY: skel

build:
	tar xzf $(DIR).tar.gz
#	for p in patches/*.patch ; do \
#	    echo "applying $$p..." ; \
#	    ( cd $(DIR) ; patch -p1 -b ) < $$p ; \
#	done
	export PERL5LIB=$(P5TMPDIST)/dest/lib/perl5; \
	    cd $(DIR) && $(PERL) Build.PL < /dev/null >build.log 2>&1
	cd $(DIR) && ./Build

install:
	rm -rf $(DESTDIR)$(OMD_ROOT)/skel/etc/jmx4perl
	mkdir -p $(DESTDIR)$(OMD_ROOT)/skel/etc/jmx4perl
	rsync -a $(DIR)/config $(DESTDIR)$(OMD_ROOT)/skel/etc/jmx4perl/
	chmod 644 $(DESTDIR)$(OMD_ROOT)/skel/etc/jmx4perl/config/*.cfg
	cp -p $(DIR)/blib/script/jmx4perl $(DESTDIR)$(OMD_ROOT)/bin/
	cp -p $(DIR)/blib/script/j4psh $(DESTDIR)$(OMD_ROOT)/bin/
	cp -p $(DIR)/blib/script/jolokia $(DESTDIR)$(OMD_ROOT)/bin/
	[ -d $(DESTDIR)$(OMD_ROOT)/lib/nagios/plugins ] || mkdir -p $(DESTDIR)$(OMD_ROOT)/lib/nagios/plugins
	cp -p $(DIR)/blib/script/check_jmx4perl $(DESTDIR)$(OMD_ROOT)/lib/nagios/plugins/
	[ -d $(DESTDIR)$(OMD_ROOT)/lib/perl5/lib/perl5 ] || mkdir -p $(DESTDIR)$(OMD_ROOT)/lib/perl5/lib/perl5
	rsync -a $(DIR)/blib/lib/ $(DESTDIR)$(OMD_ROOT)/lib/perl5/lib/perl5
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/man/man1
	rsync -a $(DIR)/blib/bindoc/ $(DESTDIR)$(OMD_ROOT)/share/man/man1
	test -d $(DESTDIR)$(OMD_ROOT)/share/doc/jmx4perl || \
	        mkdir -p $(DESTDIR)$(OMD_ROOT)/share/doc/jmx4perl
	install -m 644 README $(DESTDIR)$(OMD_ROOT)/share/doc/jmx4perl
# Jolokia Agents
	rm -rf $(DESTDIR)$(OMD_ROOT)/share/jmx4perl
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/jmx4perl/jolokia-$(JOLOKIA_VERSION)
	rsync -a jolokia-agents/$(JOLOKIA_VERSION)/ $(DESTDIR)$(OMD_ROOT)/share/jmx4perl/jolokia-$(JOLOKIA_VERSION)/
	chmod 644 $(DESTDIR)$(OMD_ROOT)/share/jmx4perl/jolokia-$(JOLOKIA_VERSION)/*

skel:

clean:
	rm -rf $(DIR)
