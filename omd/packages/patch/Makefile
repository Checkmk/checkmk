include ../../Makefile.omd

NAME     = patch
VERSION  = 2.7.6
DIR      = patch-$(VERSION)

.PHONY: build install skel clean

build:
	tar xzf patch-$(VERSION).tar.gz
	cd $(DIR) && ./configure --prefix=$(OMD_ROOT)
	$(MAKE) -C $(DIR)

install:
	$(MAKE) DESTDIR=$(DESTDIR) -C $(DIR) install

skel:

clean:
	rm -rf $(DIR)
