include ../../Makefile.omd

# This package contains the SNAP 7 library (http://snap7.sourceforge.net/)
NAME     = snap7
VERSION  = 1.4.2
DIR      = $(NAME)-full-$(VERSION)

ARCH = $(shell uname -m)
ifeq ($(ARCH),i686)
    ARCH=i386
endif

.PHONY: build install skel clean

build: check-python
	7z x $(DIR).7z
	cd $(DIR)/build/unix && $(MAKE) -f $(ARCH)_linux.mk

install:
	mkdir -p $(DESTDIR)$(OMD_ROOT)/lib
	install -m 644 $(DIR)/build/bin/$(ARCH)-linux/libsnap7.so $(DESTDIR)$(OMD_ROOT)/lib

skel:

clean:
	rm -rf $(DIR) $(PY_DIR)
