include ../../Makefile.omd

NAME     = mod_wsgi
VERSION  = 4.6.4
DIR      = $(NAME)-$(VERSION)

# Try to find the apxs binary
ifneq ("$(wildcard /usr/sbin/apxs)","")
    APXS=/usr/sbin/apxs
endif
ifneq ("$(wildcard /usr/sbin/apxs2)","")
    APXS=/usr/sbin/apxs2
endif
ifneq ("$(wildcard /usr/bin/apxs2)","")
    APXS=/usr/bin/apxs2
endif


build: check-python
	tar xzf $(DIR).tar.gz
	
	set -e ; \
	export PYTHONPATH="$$PYTHONPATH:$(PACKAGE_PYTHON_PYTHONPATH)" ; \
	export LDFLAGS="$(PACKAGE_PYTHON_LDFLAGS)" ; \
	export LD_LIBRARY_PATH="$(PACKAGE_PYTHON_LD_LIBRARY_PATH)" ; \
	export CFLAGS="-I$(PACKAGE_PYTHON_DESTDIR)/include/python2.7" ; \
	cd $(DIR) ; \
	./configure \
	    --prefix=$(OMD_ROOT) \
	    --with-apxs=$(APXS) \
	    --with-python=$(PACKAGE_PYTHON_EXECUTABLE) ; \
	make

install:
	mkdir -p $(DESTDIR)$(OMD_ROOT)/lib/apache/modules
	cp $(DIR)/src/server/.libs/mod_wsgi.so $(DESTDIR)$(OMD_ROOT)/lib/apache/modules
	chmod 644 $(DESTDIR)$(OMD_ROOT)/lib/apache/modules/mod_wsgi.so

skel:

clean:
	rm -rf $(NAME)-[0-9].[0-9].[0-9]
