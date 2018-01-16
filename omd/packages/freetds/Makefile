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
		--prefix=$(OMD_ROOT) \
		--sysconfdir=/etc/freetds \
		--with-tdsver=7.1 \
		--disable-apps \
		--disable-server \
		--disable-pool \
		--disable-odbc
	$(MAKE) -C $(DIR) -j4
# Package python-modules needs some stuff during the build.
	$(MAKE) -C $(DIR)/include prefix=$(PACKAGE_FREETDS_DESTDIR) install
	$(MAKE) -C $(DIR)/src/dblib prefix=$(PACKAGE_FREETDS_DESTDIR) install

install:
# At runtime we need only the libraries.
	$(MAKE) -C $(DIR)/src/dblib DESTDIR=$(DESTDIR) install

skel:

clean:
	rm -rf $(DIR)
