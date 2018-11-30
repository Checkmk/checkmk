include ../../Makefile.omd

NAME = mk-livestatus
DIR = $(NAME)-$(CMK_VERSION)

# Attention: copy-n-paste from check_mk/Makefile below...
build: clean check-re2
	if [ ! -f ../../../$(DIR).tar.gz ]; then \
	    $(MAKE) -C ../../.. $(DIR).tar.gz ; \
	fi
	tar xzf ../../../$(DIR).tar.gz
	cd $(DIR) && \
	./configure CXXFLAGS="-g -O3 -Wall -Wextra" --with-boost="$(PACKAGE_BOOST_DESTDIR)" --with-re2="$(PACKAGE_RE2_DESTDIR)" --prefix=$(OMD_ROOT)
	$(MAKE) -C $(DIR) all

install:
	$(MAKE) DESTDIR=$(DESTDIR) -C $(DIR) install
	mkdir -p $(DESTDIR)$(OMD_ROOT)/bin
	install -m 755 lq $(DESTDIR)$(OMD_ROOT)/bin
	mkdir -p $(DESTDIR)$(OMD_ROOT)/lib/python
	install -m 644 $(DIR)/api/python/livestatus.py $(DESTDIR)$(OMD_ROOT)/lib/python

skel:

clean:
	rm -rf mk-livestatus-*.*.*[0-9]
