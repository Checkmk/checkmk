include ../../Makefile.omd

NAME     = cma
VERSION  = $(OMD_VERSION)
DISTRO   = $(shell ../../distro)

build:

install:
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/check_mk/web/plugins/sidebar
	install -m 644 webconf_snapin.py $(DESTDIR)$(OMD_ROOT)/share/check_mk/web/plugins/sidebar
	mkdir -p $(DESTDIR)$(OMD_ROOT)/lib/cma
	install -m 755 post-install $(DESTDIR)$(OMD_ROOT)/lib/cma

skel:

clean:
