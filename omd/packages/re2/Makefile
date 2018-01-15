include ../../Makefile.omd

# We use a released version from https://github.com/google/re2/, but in
# principle we could use any tag by exporting it manually via:
#    ( TAG=2018-01-01; git archive --prefix=re2-$TAG/ --output=re2-$TAG.tar.gz $TAG )
NAME     = re2
VERSION  = 2018-01-01
DIR      = $(NAME)-$(VERSION)

.PHONY: build install skel clean

build:
	tar xzf $(DIR).tar.gz
	$(MAKE) -C $(DIR) DESTDIR=$(abspath dest) prefix=$(OMD_ROOT) install

install:

skel:

clean:
	rm -rf $(DIR) dest
