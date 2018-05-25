include ../../Makefile.omd

# This package contains the SNAP 7 library (http://snap7.sourceforge.net/)
NAME     = snap7
VERSION  = 1.3.0
DIR      = snap7-full-$(VERSION)

ARCH = $(shell uname -m)
ifeq ($(ARCH),i686)
    ARCH=i386
endif

.PHONY: build install skel clean

build: check-python
	tar xzf $(DIR).tar.gz
	cd $(DIR)/build/unix && $(MAKE) -f $(ARCH)_linux.mk

install:
	mkdir -p $(DESTDIR)$(OMD_ROOT)/lib
	install -m 644 $(DIR)/build/bin/$(ARCH)-linux/libsnap7.so $(DESTDIR)$(OMD_ROOT)/lib

skel:

clean:
	rm -rf $(DIR) $(PY_DIR)
