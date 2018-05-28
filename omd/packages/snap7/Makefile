include ../../Makefile.omd

# This package contains the SNAP 7 library (http://snap7.sourceforge.net/)
NAME     = snap7
VERSION  = 1.4.2
DIR      = $(NAME)-full-$(VERSION)

ARCH = $(shell uname -m)
ifeq ($(ARCH),i686)
    ARCH=i386
endif

.PHONY: build install skel clean repackage

build: check-python
	tar xzf $(DIR).tar.gz
	$(MAKE) -C $(DIR)/build/unix -f $(ARCH)_linux.mk

install:
	mkdir -p $(DESTDIR)$(OMD_ROOT)/lib
	install -m 644 $(DIR)/build/bin/$(ARCH)-linux/libsnap7.so $(DESTDIR)$(OMD_ROOT)/lib

skel:

clean:
	rm -rf $(DIR) $(DIR).7z

# The original 7z file is quite large (20MB), because it contains tons of
# executables, but we don't need any of them. An equivalent .tar.gz would almost
# be 60MB. Furthermore, requiring a 7z command at build time on a ton of
# platforms is annoying (adding repos, varying names, etc.), so we repackage the
# 7z file to a standard gzipped tar file.
repackage: clean
	wget https://sourceforge.net/projects/snap7/files/$(VERSION)/$(DIR).7z
	7z x $(DIR).7z
	GZIP=-9 tar cvzf $(DIR).tar.gz $(DIR)/build $(DIR)/src $(DIR)/*.txt
