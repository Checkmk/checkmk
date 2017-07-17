include ../../Makefile.omd

NAME     = patch
VERSION  = 2.6
DIR      = patch-$(VERSION)

.PHONY: skel

build:
	test -f patch-${VERSION}.tar.gz || wget "ftp://ftp.gnu.org/gnu/patch/patch-${VERSION}.tar.gz"
	tar xzf patch-$(VERSION).tar.gz
	cd $(DIR) && ./configure --prefix=$(OMD_ROOT)
	cd $(DIR) && $(MAKE)

install:
	$(MAKE) DESTDIR=$(DESTDIR) -C $(DIR) install

skel:

clean:
	rm -rf $(DIR)
