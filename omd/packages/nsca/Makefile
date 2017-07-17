include ../../Makefile.omd

NAME = nsca
VERSION = 2.9.1
DIR = $(NAME)-$(VERSION)

.PHONY: skel

# Configure options for Nagios. Since we want to compile
# as non-root, we use our own user and group for compiling.
# All files will be packaged as user 'root' later anyway.
CONFIGUREOPTS = ""

build:
	tar xzf $(DIR).tar.gz
	for p in patches/*.diff ; do \
          echo "applying $$p..." ; \
          patch -p1 -b -d $(DIR) < $$p ; \
        done
	cd $(DIR) ; ./configure $(CONFIGUREOPTS)
	$(MAKE) -C $(DIR) all

install:
	install -m 755 $(DIR)/src/nsca $(DESTDIR)$(OMD_ROOT)/bin
	install -m 755 $(DIR)/src/send_nsca $(DESTDIR)$(OMD_ROOT)/bin

	mkdir $(DESTDIR)$(OMD_ROOT)/share/doc/nsca
	install -m 644 $(DIR)/README $(DESTDIR)$(OMD_ROOT)/share/doc/nsca
	install -m 644 $(DIR)/LEGAL $(DESTDIR)$(OMD_ROOT)/share/doc/nsca
	install -m 644 $(DIR)/SECURITY $(DESTDIR)$(OMD_ROOT)/share/doc/nsca

skel:

clean:
	rm -rf $(DIR)
