include ../../Makefile.omd

NAME     = net-snmp
VERSION  = 734f855
DIR      = $(NAME)-$(VERSION)

.PHONY: skel

build: check-python
	tar xzf $(NAME)-$(VERSION).tar.gz
	set -e ; for p in patches/*.dif ; do \
	    echo "applying $$p..." ; \
	    patch -p1 -b -d $(DIR) < $$p ; \
	done
# Skip Perl-Modules because of build errors when MIB loading is disabled.
# Skip Python binding because we need to use our own python, see install target.
	cd $(DIR) && ./configure \
	    --enable-ipv6 \
	    --disable-agent \
	    --disable-snmptrapd-subagent \
	    --with-mibdirs="\$$HOME/local/share/snmp/mibs:$(OMD_ROOT)/share/snmp/mibs:/usr/share/snmp/mibs" \
	    --with-defaults \
	    --disable-scripts \
	    --prefix=$(OMD_ROOT) && make

install:
	cd $(DIR)/snmplib && make DESTDIR=$(DESTDIR) installlibs
	cd $(DIR)/apps && make DESTDIR=$(DESTDIR) installbin
	cd $(DIR)/man && make DESTDIR=$(DESTDIR) install
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/snmp/mibs
	cd $(DIR)/mibs && make DESTDIR=$(DESTDIR) mibsinstall
	mkdir -p $(DESTDIR)$(OMD_ROOT)/lib/python
	cd $(DIR)/python && \
	    export PYTHONPATH="$$PYTHONPATH:$(PACKAGE_PYTHON_PYTHONPATH)" ; \
	    export LDFLAGS="$(PACKAGE_PYTHON_LDFLAGS)" ; \
	    export LD_LIBRARY_PATH="$(PACKAGE_PYTHON_LD_LIBRARY_PATH)" ; \
	    $(PACKAGE_PYTHON_EXECUTABLE) setup.py install --basedir=.. --home=$(DESTDIR)$(OMD_ROOT) \
	        --prefix='' \
	        --install-platlib=$(DESTDIR)$(OMD_ROOT)/lib/python \
	        --install-purelib=$(DESTDIR)$(OMD_ROOT)/lib/python
# For some obscure reason beyond the mental capacities of mere humans, the
# easy_install mechanism triggered by the setup call above results in the
# creation of a lib/python/site.py, a copy of site-patch.py from setuptools.
# Having this in the PYTHONPATH makes it impossible to run python3-based SW as a
# site user, including gdb! So let's simply nuke it here...
	$(RM) $(DESTDIR)$(OMD_ROOT)/lib/python/site.py*

skel:

clean:
	rm -rf $(DIR)
