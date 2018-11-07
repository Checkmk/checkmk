include ../../Makefile.omd

NAME     = libgsf
VERSION  = 1.14.44
DIR      = libgsf-$(VERSION)

.PHONY: build install skel clean

build:
	tar xJf $(DIR).tar.xz
	cd $(DIR) && ./configure --prefix=$(OMD_ROOT)
	$(MAKE) -C $(DIR)

install:
	$(MAKE) DESTDIR=$(DESTDIR) -C $(DIR) install

skel:

clean:
	rm -rf $(DIR)
