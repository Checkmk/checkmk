include ../../Makefile.omd

NAME       := boost
VERSION    := 1_68_0
DIR        := $(NAME)_$(VERSION)

# For some obscure reason (GCC's dual ABI) we have to link all Boost stuff
# statically, otherwise we get linker errors later, e.g.:
#
#    .../packages/boost/destdir/lib/libboost_system.so: undefined reference to `std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_create(unsigned long&, unsigned long)@GLIBCXX_3.4.21'
#    .../packages/boost/destdir/lib/libboost_system.so: undefined reference to `std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::~basic_string()@GLIBCXX_3.4.21'
#    .../packages/boost/destdir/lib/libboost_system.so: undefined reference to `operator delete(void*, unsigned long)@CXXABI_1.3.9'
#
# For more details about the dual ABI see:
#
#    https://gcc.gnu.org/onlinedocs/gcc-5.2.0/libstdc++/manual/manual/using_dual_abi.html
#    https://developers.redhat.com/blog/2015/02/05/gcc5-and-the-c11-abi/
B2_LINK_OPTION := "link=static"

.PHONY: build install skel clean

build: check-python
	tar xjf $(NAME)_$(VERSION).tar.bz2
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
	echo "using gcc : : $$CXX ;" > $(DIR)/tools/build/src/user-config.jam
	( cd $(DIR) && \
	  export PYTHONPATH="$$PYTHONPATH:$(PACKAGE_PYTHON_PYTHONPATH)" ; \
	  export LDFLAGS="$(PACKAGE_PYTHON_LDFLAGS)" ; \
	  export LD_LIBRARY_PATH="$(PACKAGE_PYTHON_LD_LIBRARY_PATH)" ; \
	  ./bootstrap.sh \
	    "--prefix=$(PACKAGE_BOOST_DESTDIR)" \
      "--without-libraries=graph,locale,log,math,program_options,regex,serialization,wave" \
	    "--with-python=$(PACKAGE_PYTHON_EXECUTABLE)" && \
	  ./b2 $(B2_LINK_OPTION) cxxflags=-fPIC cflags=-fPIC -j2 install )

install:
	mkdir -p $(DESTDIR)$(OMD_ROOT)/lib
	find $(PACKAGE_BOOST_DESTDIR)/lib -name "*.so*" -exec cp -v {} $(DESTDIR)$(OMD_ROOT)/lib \;

skel:

clean:
	rm -rf $(DIR) $(PACKAGE_BOOST_DESTDIR)
