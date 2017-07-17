include ../../Makefile.omd

NAME     = mod_fcgid
VERSION  = 2.3.9
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

build:
	tar xzf $(DIR).tar.gz
	set -e ; for p in patches/*.patch ; do \
	    echo "applying $$p..." ; \
	    patch -p1 -b -d $(DIR) < $$p ; \
	done
	
	cd $(DIR) && APXS=$(APXS) ./configure.apxs
	CPATH="/usr/include/apache2-worker" $(MAKE) -C $(DIR)

install:
	mkdir -p $(DESTDIR)$(OMD_ROOT)/lib/apache/modules
	cp $(DIR)/modules/fcgid/.libs/mod_fcgid.so $(DESTDIR)$(OMD_ROOT)/lib/apache/modules
	chmod 644 $(DESTDIR)$(OMD_ROOT)/lib/apache/modules/mod_fcgid.so

skel:
	mkdir -p $(SKEL)/tmp/apache/fcgid_sock

clean:
	rm -rf $(DIR)
