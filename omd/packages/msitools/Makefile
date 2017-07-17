include ../../Makefile.omd

NAME         = msitools
VERSION      = 0.94
DIR          = msitools-$(VERSION)

LCAB_VERSION = 1.0b12
LCAB_DIR     = lcab-$(LCAB_VERSION)

.PHONY: skel


# Problem here is: msitools is not compilable on older distros
# like Debian 5 or RedHat 5.X. So here we rather ignore
# compile problems and msi{build,info} will be missing. Check_MK
# then nows this and the agent bakery cannot create MSI
# packages. People need to upgrade to a more modern platform
# for that.

build:
	$(MAKE) prep
	# Do not try to compile on lenny. Compiler is too old
	if [ "$$(gcc --version | sed -n '1s/.* //p' )" != 4.3.2 ] && cd $(DIR) && ./configure --prefix=$(OMD_ROOT) ; then \
	  make -C libmsi ; \
	  make msibuild ; \
	  make msiinfo ; \
	fi
	cd $(LCAB_DIR) && ./configure && make

prep:
	rm -rf $(DIR)
	tar xzf $(DIR).tar.gz
	set -e ; for p in patches/*.dif ; do \
	  echo "applying $$p..." ; \
	      patch -p1 -b -d $(DIR) < $$p ; \
	  done
	tar xzf $(LCAB_DIR).tar.gz

install:
	if [ -f $(DIR)/.libs/msiinfo ] ; then \
	    mkdir -p $(DESTDIR)$(OMD_ROOT)/bin ; \
	    install -m 755 $(DIR)/.libs/msiinfo $(DESTDIR)$(OMD_ROOT)/bin ; \
	    install -m 755 $(DIR)/.libs/msibuild $(DESTDIR)$(OMD_ROOT)/bin ; \
	    install -m 755 $(LCAB_DIR)/lcab $(DESTDIR)$(OMD_ROOT)/bin ; \
	    mkdir -p $(DESTDIR)$(OMD_ROOT)/lib ; \
	    install -m 755 $(DIR)/libmsi/.libs/libmsi.so* $(DESTDIR)$(OMD_ROOT)/lib ; \
	    mkdir -p $(DESTDIR)$(OMD_ROOT)/share/check_mk/agents/windows ; \
	    install -m 644 *.msi $(DESTDIR)$(OMD_ROOT)/share/check_mk/agents/windows ; \
	fi

skel:

clean:
	rm -rf $(DIR) $(LCAB_DIR)

