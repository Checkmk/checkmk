include ../../Makefile.omd

# We use a released version from https://github.com/google/re2/, but in
# principle we could use any tag by exporting it manually via:
#    ( TAG=2018-02-01; git archive --prefix=re2-$TAG/ --output=re2-$TAG.tar.gz $TAG )
NAME     := re2
VERSION  := 2018-10-01
DIR      := $(NAME)-$(VERSION)

BUILD-HELPER-DIR := .$(NAME)-build-helper

TARXZ := $(shell which tar) xzf
TOUCH := $(shell which touch)
MKDIR := $(shell which mkdir) -p

.PHONY: build unpacks install skel clean

build: $(BUILD-HELPER-DIR)/build

unpack: $(BUILD-HELPER-DIR)/unpack


$(BUILD-HELPER-DIR)/build: $(BUILD-HELPER-DIR)/unpack
# basically what part of AC_PROC_CXX does
	@CXX="" ; \
	for PROG in g++-8 clang++-7 g++-7 clang++-6.0 clang++-5.0 g++-6 clang++-4.0 g++-5 clang++-3.9 clang++-3.8 clang++-3.7 clang++-3.6 clang++-3.5 g++-4.9 g++ clang++; do \
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
	$(MAKE) -C $(DIR) CXX="$$CXX" CPPFLAGS="-DRE2_ON_VALGRIND" CXXFLAGS="-O3 -g -fPIC" DESTDIR=$(PACKAGE_RE2_DESTDIR) prefix=$(OMD_ROOT) install
# Note: We need the -fPIC above to link RE2 statically into livestatus.o.
# TODO(sp): What should we do about RE2_ON_VALGRIND?
# Massage paths a bit by moving things around.
	mv $(PACKAGE_RE2_DESTDIR)/$(OMD_ROOT)/include  $(PACKAGE_RE2_DESTDIR)/$(OMD_ROOT)/lib $(PACKAGE_RE2_DESTDIR)
	$(RM) -r $(PACKAGE_RE2_DESTDIR)/$(OMD_BASE)
# To link statically against RE2, we must *only* see the static library at link
# time. It is a bit wasteful to build the dynamic library, too, but RE2's
# Makefile doesn't offer an easy way around that.
	$(RM) $(PACKAGE_RE2_DESTDIR)/lib/*.so*
	$(TOUCH) $@

$(BUILD-HELPER-DIR)/unpack: $(DIR).tar.gz
	$(MKDIR) $(BUILD-HELPER-DIR)
	$(TARXZ) $<
	$(TOUCH) $@

install:

skel:

clean:
	$(RM) -r $(DIR) $(PACKAGE_RE2_DESTDIR) $(BUILD-HELPER-DIR)
