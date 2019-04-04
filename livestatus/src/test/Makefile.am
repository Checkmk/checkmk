# .------------------------------------------------------------------------.
# |                ____ _               _        __  __ _  __              |
# |               / ___| |__   ___  ___| | __   |  \/  | |/ /              |
# |              | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /               |
# |              | |___| | | |  __/ (__|   <    | |  | | . \               |
# |               \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\              |
# |                                        |_____|                         |
# |             _____       _                       _                      |
# |            | ____|_ __ | |_ ___ _ __ _ __  _ __(_)___  ___             |
# |            |  _| | '_ \| __/ _ \ '__| '_ \| '__| / __|/ _ \            |
# |            | |___| | | | ||  __/ |  | |_) | |  | \__ \  __/            |
# |            |_____|_| |_|\__\___|_|  | .__/|_|  |_|___/\___|            |
# |                                     |_|                                |
# |                     _____    _ _ _   _                                 |
# |                    | ____|__| (_) |_(_) ___  _ __                      |
# |                    |  _| / _` | | __| |/ _ \| '_ \                     |
# |                    | |__| (_| | | |_| | (_) | | | |                    |
# |                    |_____\__,_|_|\__|_|\___/|_| |_|                    |
# |                                                                        |
# | mathias-kettner.com                                 mathias-kettner.de |
# '------------------------------------------------------------------------'
#  This file is part of the Check_MK Enterprise Edition (CEE).
#  Copyright by Mathias Kettner and Mathias Kettner GmbH.  All rights reserved.
#
#  Distributed under the Check_MK Enterprise License.
#
#  You should have  received  a copy of the Check_MK Enterprise License
#  along with Check_MK. If not, email to mk@mathias-kettner.de
#  or write to the postal address provided at www.mathias-kettner.de

CLANG_VERSION ?= 7

BEAR ?= bear
CPPCHECK ?= cppcheck
IWYU_TOOL ?= iwyu_tool
RUN_CLANG_TIDY ?= run-clang-tidy-$(CLANG_VERSION).py

GOOGLETEST :=$(top_srcdir)/omd/packages/googletest

bin_PROGRAMS = test_neb

test_neb_SOURCES = \
    DummyNagios.cc \
    test_OffsetStringMacroColumn.cc
test_neb_CPPFLAGS = \
    -I.. \
    -I../.. \
    -I$(GOOGLETEST)/destdir/include \
    @BOOST_CPPFLAGS@ @RE2_CPPFLAGS@
test_neb_LDFLAGS = \
    -static-libstdc++ \
    $(GOOGLETEST)/destdir/lib/libgtest_main.a \
    $(GOOGLETEST)/destdir/lib/libgtest.a \
    @BOOST_LDFLAGS@ \
    @RE2_LDFLAGS@
test_neb_LDADD = \
    -lstdc++fs \
    ../liblivestatus.a \
    -lpthread \
    @BOOST_ASIO_LIB@ \
    @RE2_LIBS@

.PHONY: unit-test build_googletest

unit-test: test_neb$(EXEEXT)
	GTEST_OUTPUT=xml ./test_neb$(EXEEXT)

# NOTE: This is a bit of a hack. What we really want is a clean chroot/VM/image
# where we just install our build dependencies.
$(test_neb_SOURCES): build_googletest

build_googletest:
	$(MAKE) -C $(GOOGLETEST) build

compile_commands.json: Makefile $(wildcard *.cc  *.h)
	$(MAKE) clean
# HACK: bear doeesn't have an option to exclude some parts in the output, so we
# make sure that googletest is built first. We don't want to include that...
	$(MAKE) -C ../../.. config.status
	$(MAKE) -j4 -C ..
	$(BEAR) $(MAKE) -j4 test_neb

tidy: compile_commands.json
	$(RUN_CLANG_TIDY) -quiet -j6 $(FILES_TO_CHECK)

iwyu: compile_commands.json
	$(IWYU_TOOL) --output-format=clang -p . $(FILES_TO_CHECK) -- --mapping_file=$(abs_top_srcdir)/livestatus/iwyu-mappings/check_mk.imp

# NOTE: cppcheck seems to ignore files on the command line when --project=... is given.  :-P
cppcheck: compile_commands.json
	$(CPPCHECK) -UCMC --enable=all --suppressions-list=../cppcheck-suppressions.txt --inline-suppr --project=compile_commands.json --quiet --template=gcc

cppcheck-xml: compile_commands.json
	$(CPPCHECK) -UCMC --enable=all --suppressions-list=../cppcheck-suppressions.txt --inline-suppr --project=compile_commands.json --quiet --template=gcc --xml --xml-version=2 2> cppcheck-result.xml
