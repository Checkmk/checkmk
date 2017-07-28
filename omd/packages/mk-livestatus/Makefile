include ../../Makefile.omd

NAME = mk-livestatus
DIR = $(NAME)-$(CMK_VERSION)
CXX_FLAGS := -g -O3 -Wall -Wextra

# Attention: copy-n-paste from check_mk/Makefile below...
build: clean
	if [ ! -f ../../../$(DIR).tar.gz ]; then \
	    $(MAKE) -C ../../.. $(DIR).tar.gz ; \
	fi
	tar xzf ../../../$(DIR).tar.gz
	@if test -d ../boost/local ; then \
	  BOOST_OPT="--with-boost=$(abspath ../boost/local)" ; \
	elif test -d ../cmk-omd/packages/boost/local ; then \
	  BOOST_OPT="--with-boost=$(abspath ../cmk-omd/packages/boost/local)" ; \
	elif test ! -d /usr/include/boost -a -d /usr/include/boost141/boost ; then \
	  BOOST_OPT="CPPFLAGS=-I/usr/include/boost141" ; \
	else \
	  BOOST_OPT="DUMMY1=" ; \
	fi ; \
	cd $(DIR) && \
	echo ./configure CXXFLAGS="$(CXX_FLAGS)" "$$BOOST_OPT" --prefix=$(OMD_ROOT) && \
	./configure CXXFLAGS="$(CXX_FLAGS)" "$$BOOST_OPT" --prefix=$(OMD_ROOT)
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
