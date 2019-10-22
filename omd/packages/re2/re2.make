# We use a released version from https://github.com/google/re2/, but in
# principle we could use any tag by exporting it manually via:
#    ( TAG=2018-02-01; git archive --prefix=re2-$TAG/ --output=re2-$TAG.tar.gz $TAG )
RE2 := re2
RE2_VERS := 2019-09-01
RE2_DIR := $(RE2)-$(RE2_VERS)

RE2_BUILD := $(BUILD_HELPER_DIR)/$(RE2_DIR)-build
RE2_UNPACK := $(BUILD_HELPER_DIR)/$(RE2_DIR)-unpack

.PHONY: $(RE2) $(RE2)-install $(RE2)-skel $(RE2)-clean

$(RE2): $(RE2_BUILD)

$(RE2)-install:

$(RE2_BUILD): $(RE2_UNPACK)
# basically what part of AC_PROC_CXX does
	@CXX="" ; \
	for PROG in g++-9 clang++-8 g++-8 clang++-7 g++-7 clang++-6.0 clang++-5.0 g++ clang++; do \
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
	$(MKDIR) $(RE2_DIR) && \
	cd $(RE2_DIR) && \
	cmake -DCMAKE_CXX_COMPILER="$$CXX" \
        -DCMAKE_CXX_FLAGS="-DRE2_ON_VALGRIND -O3 -g -fPIC" \
        -DCMAKE_INSTALL_PREFIX="$(PACKAGE_RE2_DESTDIR)" \
        -DCMAKE_INSTALL_LIBDIR="lib" \
        -DRE2_BUILD_TESTING="OFF" \
        .
# Note: We need the -fPIC above to link RE2 statically into livestatus.o.
	cmake --build $(RE2_DIR) --target install -- -j 4
	$(TOUCH) $@

$(RE2)-skel:

$(RE2)-clean:
	$(RM) -r $(RE2_DIR) $(PACKAGE_RE2_DESTDIR) $(BUILD_HELPER_DIR)/$(RE2)*
