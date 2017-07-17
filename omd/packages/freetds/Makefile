include ../../Makefile.omd

NAME     = freetds
VERSION  = 0.95.95
DIR      = $(NAME)-$(VERSION)

.PHONY: build install skel clean

build:
	tar xzf $(DIR).tar.gz
	cd $(DIR) && \
	    ./configure \
		--enable-msdblib \
		--prefix=/usr \
		--sysconfdir=/etc/freetds \
		--with-tdsver=7.1 \
		--disable-apps \
		--disable-server \
		--disable-pool \
		--disable-odbc \
	       	&& \
	    $(MAKE) -j4

install:
	mkdir -p $(DESTDIR)$(OMD_ROOT)/lib
	install -m 644 $(DIR)/src/ctlib/.libs/libct.so $(DESTDIR)$(OMD_ROOT)/lib/
	install -m 644 $(DIR)/src/dblib/.libs/libsybdb.so $(DESTDIR)$(OMD_ROOT)/lib/

skel:

clean:
	rm -rf $(DIR)
