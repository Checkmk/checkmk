include ../../Makefile.omd

NAME     = libgsf
VERSION  = 1.14.44
DIR      = libgsf-$(VERSION)

.PHONY: build install skel clean

build:
ifneq ($(filter $(DISTRO_CODE),sles15),)
	tar xJf $(DIR).tar.xz
	cd $(DIR) && ./configure --prefix=$(OMD_ROOT)
	$(MAKE) -C $(DIR)
endif

install:
ifneq ($(filter $(DISTRO_CODE),sles15),)
	$(MAKE) DESTDIR=$(DESTDIR) -C $(DIR) install
endif

skel:

clean:
	rm -rf $(DIR)
