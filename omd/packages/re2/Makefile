include ../../Makefile.omd

# We use a released version from https://github.com/google/re2/, but in
# principle we could use any tag by exporting it manually via:
#    ( TAG=2018-02-01; git archive --prefix=re2-$TAG/ --output=re2-$TAG.tar.gz $TAG )
NAME     = re2
VERSION  = 2018-02-01
DIR      = $(NAME)-$(VERSION)

.PHONY: build install skel clean

build:
	tar xzf $(DIR).tar.gz
# basically what part of AC_PROC_CXX does
	@CXX="" ; \
	for PROG in g++-7 clang++-5.0 g++-6 clang++-4.0 g++-5 clang++-3.9 clang++-3.8 clang++-3.7 clang++-3.6 clang++-3.5 g++-4.9 g++ clang++; do \
	    echo -n "checking for $$PROG... "; SAVED_IFS=$$IFS; IFS=: ; \
	    for DIR in $$PATH; do \
	        IFS=$$SAVED_IFS ; \
	        test -z "$$DIR" && DIR=. ; \
	        ABS_PROG="$$DIR/$$PROG" ; \
	        test -x "$$ABS_PROG" && { CXX="$$ABS_PROG"; echo "$$CXX"; break 2; } ; \
	    done ; \
	    echo "no"; IFS=$$SAVED_IFS ; \
	done ; \
	test -z "$$CXX" && { echo "error: no C++ compiler found" >&2 ; exit 1; } ; \
	$(MAKE) -C $(DIR) CXX="$$CXX" CPPFLAGS="-DRE2_ON_VALGRIND" DESTDIR=$(PACKAGE_RE2_DESTDIR) prefix=$(OMD_ROOT) install
# TODO(sp): What should we do about RE2_ON_VALGRIND?
# Massage paths a bit by moving things around.
	mv $(PACKAGE_RE2_DESTDIR)/$(OMD_ROOT)/include  $(PACKAGE_RE2_DESTDIR)/$(OMD_ROOT)/lib $(PACKAGE_RE2_DESTDIR)
	rm -rf $(PACKAGE_RE2_DESTDIR)/$(OMD_BASE)
# The RE2 Makefile offers no mechanism to strip the libraries. :-/
	strip $(PACKAGE_RE2_DESTDIR)/lib/*.a $(PACKAGE_RE2_DESTDIR)/lib/*.so

install:
	mkdir -p $(DESTDIR)$(OMD_ROOT)
	cp -a $(PACKAGE_RE2_DESTDIR)/include $(PACKAGE_RE2_DESTDIR)/lib $(DESTDIR)$(OMD_ROOT)

skel:

clean:
	rm -rf $(DIR) $(PACKAGE_RE2_DESTDIR)
