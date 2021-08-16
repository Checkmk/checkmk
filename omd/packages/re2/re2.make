# We use a released version from https://github.com/google/re2/, but in
# principle we could use any tag by exporting it manually via:
#    ( TAG=2018-02-01; git archive --prefix=re2-$TAG/ --output=re2-$TAG.tar.gz $TAG )
RE2 := re2
RE2_VERS := 2020-06-01
RE2_DIR := $(RE2)-$(RE2_VERS)

RE2_UNPACK := $(BUILD_HELPER_DIR)/$(RE2_DIR)-unpack
RE2_BUILD := $(BUILD_HELPER_DIR)/$(RE2_DIR)-build
RE2_INSTALL := $(BUILD_HELPER_DIR)/$(RE2_DIR)-install

#RE2_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(RE2_DIR)
RE2_BUILD_DIR := $(PACKAGE_BUILD_DIR)/$(RE2_DIR)
#RE2_WORK_DIR := $(PACKAGE_WORK_DIR)/$(RE2_DIR)
# Used by other packages
PACKAGE_RE2_DESTDIR := $(PACKAGE_BASE)/re2/destdir

$(RE2_BUILD): $(RE2_UNPACK)
# basically what part of AC_PROC_CXX does
	@CXX="" ; \
	for PROG in clang++-13 g++-11 clang++-12 g++-10 clang++-11 clang++-10 g++-9 clang++-9 clang++-8 g++-8 clang++-7 g++-7 clang++-6.0 clang++-5.0 g++ clang++; do \
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
	cd $(RE2_BUILD_DIR) && \
	cmake -DCMAKE_CXX_COMPILER="$$CXX" \
        -DCMAKE_CXX_FLAGS="-DRE2_ON_VALGRIND -O3 -g -fPIC" \
        -DCMAKE_INSTALL_PREFIX="$(PACKAGE_RE2_DESTDIR)" \
        -DCMAKE_INSTALL_LIBDIR="lib" \
        -DRE2_BUILD_TESTING="OFF" \
        .
# Note: We need the -fPIC above to link RE2 statically into livestatus.o.
	unset DESTDIR MAKEFLAGS; \
	    cmake --build $(RE2_BUILD_DIR) --target install -- -j 4
	$(TOUCH) $@

$(RE2_INSTALL):
	$(TOUCH) $@
