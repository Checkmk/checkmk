# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2018             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

bin_PROGRAMS = check_mk_agent
check_PROGRAMS = WindowsAgentTest WindowsAgentCoverage wmitest
noinst_LIBRARIES = libcheck_mk_agent.a libcheck_mk_agent_coverage.a
noinst_PROGRAMS = MontyPython

AUTOMAKE_OPTIONS = foreign
AM_CPPFLAGS = -I$(top_srcdir)/sections -O2 -Wformat=2 -Werror -Wall -fno-rtti \
              -std=c++17 -gdwarf-2 -DCHECK_MK_VERSION='"$(VERSION)"' \
              -D__USE_MINGW_ANSI_STDIO -DSI_SUPPORT_IOSTREAMS
AM_LDFLAGS = -static -static-libgcc -static-libstdc++
LD_COMMON = -lwsock32 -lws2_32 -lole32 -loleaut32 -lwbemuuid -lpsapi -lshlwapi -limagehlp -lstdc++fs
GTEST_LDFLAGS = -lgtest -lgmock
COVERAGE_COMPILER_FLAGS = -fprofile-arcs -ftest-coverage
COVERAGE_LINKER_FLAGS = -lgcov --coverage

check_mk_agent_LDADD = check_mk_agent.res libcheck_mk_agent.a $(LD_COMMON)

WindowsAgentTest_CPPFLAGS = $(AM_CPPFLAGS) -I$(top_srcdir)/test
WindowsAgentTest_LDADD = libcheck_mk_agent.a $(GTEST_LDFLAGS) $(LD_COMMON)

WindowsAgentCoverage_CPPFLAGS = $(WindowsAgentTest_CPPFLAGS) $(COVERAGE_COMPILER_FLAGS)
WindowsAgentCoverage_LDFLAGS = $(AM_LDFLAGS) $(COVERAGE_LINKER_FLAGS)
WindowsAgentCoverage_LDADD = libcheck_mk_agent_coverage.a $(GTEST_LDFLAGS) $(LD_COMMON)
libcheck_mk_agent_coverage_a_CPPFLAGS = -D main=check_mk_agent_main $(WindowsAgentCoverage_CPPFLAGS)

wmitest_LDADD = $(LD_COMMON)

PYTEST = /usr/bin/env pytest
PYTEST_OPTIONS = --maxfail=10
PYTEST_JENKINS = $(PYTEST_OPTIONS) --junitxml=$(bindir)/junit.xml

libcheck_mk_agent_a_SOURCES = \
        Configuration.cc \
        CrashHandler.cc \
        Crypto.cc \
        Environment.cc \
        EventLog.cc \
        EventLogBase.cc \
        EventLogVista.cc \
        ExternalCmd.cc \
        ListenSocket.cc \
        Logger.cc \
        OHMMonitor.cc \
        OutputProxy.cc \
        PerfCounter.cc \
        PerfCounterCommon.cc \
        RotatingFileHandler.cc \
        SectionManager.cc \
        SettingsCollector.cc \
        Thread.cc \
        WinApi.cc \
        WritableFile.cc \
        stringutil.cc \
        types.cc \
        win_error.cc \
        wmiHelper.cc \
        sections/Section.cc \
        sections/SectionCheckMK.cc \
        sections/SectionDF.cc \
        sections/SectionEventlog.cc \
        sections/SectionFileinfo.cc \
        sections/SectionGroup.cc \
        sections/SectionLogwatch.cc \
        sections/SectionMRPE.cc \
        sections/SectionMem.cc \
        sections/SectionOHM.cc \
        sections/SectionPS.cc \
        sections/SectionPerfcounter.cc \
        sections/SectionPluginGroup.cc \
        sections/SectionServices.cc \
        sections/SectionSkype.cc \
        sections/SectionSpool.cc \
        sections/SectionSystemtime.cc \
        sections/SectionUptime.cc \
        sections/SectionWMI.cc \
        sections/SectionWinperf.cc

check_mk_agent_SOURCES = check_mk_agent.cc

libcheck_mk_agent_coverage_a_SOURCES = $(libcheck_mk_agent_a_SOURCES) $(check_mk_agent_SOURCES)

MontyPython_SOURCES = it/MontyPython.cc

WindowsAgentTest_SOURCES = \
        test/ConfigurationTest.cc \
        test/EnvironmentTest.cc \
        test/EventLogVistaTest.cc \
        test/MockEnvironment.cc \
        test/MockLogger.cc \
        test/MockWinApi.cc \
        test/RotatingFileHandlerTest.cc \
        test/WritableFileTest.cc \
        test/gtest_main.cc \
        test/stringutilTest.cc \
        test/typesTest.cc \
        test/wmiHelperTest.cc \
        test/sections/SectionEventlogTest.cc \
        test/sections/SectionHeaderTest.cc \
        test/sections/SectionLogwatchTest.cc \
        test/sections/SectionMRPETest.cc

WindowsAgentCoverage_SOURCES = $(WindowsAgentTest_SOURCES)

wmitest_SOURCES = Logger.cc WinApi.cc stringutil.cc wmiHelper.cc wmitest.cc

CLEANFILES = \
        *.ico *.res *.rc config.* stamp-* Makefile \
        $$(find . -name "*.gc*") \
        $$(find . -name "*coverage.info") \
        $$(find . -name "*.html") \
        $$(find . -name "*.xml") \
        $$(find . -name .dirstamp) \
        $$(find .deps/ sections/.deps test/.deps test/sections/.deps it/.deps -type f) \
        $(addprefix $(bindir)/,$(bin_PROGRAMS)) \
        $(patsubst %$(EXEEXT),%-64$(EXEEXT),$(addprefix $(bindir)/,$(bin_PROGRAMS))) \
        $(patsubst %$(EXEEXT),%.msi,$(addprefix $(bindir)/,$(bin_PROGRAMS)))

.PHONY: unittest integrationtest coverage-reset openhardwaremonitor unittest-coverage-html

# Prevent race condition between parallel 32 and 64 bit builds by protecting
# access to build_version through a lock file.
build_version: $(check_mk_agent_SOURCES:.cc=.o)
	( \
        flock -e 200 ; \
        echo $$(( $$(cat $(VPATH)/build_version) + 1 )) > $(VPATH)/build_version \
    ) 200>/var/lock/build_version.lock

# Prevent race condition between parallel 32 and 64 bit builds by protecting
# access to build_version through a lock file.
check_mk_agent.rc: $(VPATH)/check_mk_agent.rc.in build_version
	( \
        flock -e 200 ; \
        sed -e "s/%VERSION%/$(VERSION)/g" \
            -e "s/%YEAR%/$$(date +%Y)/g" \
            -e "s/%BUILD_VERSION%/$$(cat $(VPATH)/build_version)/g" $< > $@ \
    ) 200>/var/lock/build_version.lock

check_mk_agent.res: check_mk_agent.rc $(VPATH)/check_mk_agent.ico
	cp $(VPATH)/check_mk_agent.ico check_mk_agent.ico
	$(WINDRES) $< -O coff -o $@

# Wine depends on X Server and may produce a number of warnings at startup.
# Using Xvfb does not work properly, either. Simply send those stderr warnings
# to /dev/null as the test output will go to stdout (and/or xml file) anyway.
#	DISPLAY="$$DISPLAY xterm" GTEST_OUTPUT=xml:result.xml wine $< 2>/dev/null
unittest: WindowsAgentTest$(EXEEXT)
	TERM=linux DISPLAY="$$DISPLAY xterm" GTEST_OUTPUT=xml:result.xml wine $<

integrationtest: install-strip openhardwaremonitor
	cd $(bindir)/it ; \
        rm -f remote.pyc ; \
        rm -rf __pycache__ ; \
        if [[ $$USER == jenkins ]] ; then \
          $(PYTEST) $(PYTEST_JENKINS) ; \
        else \
          $(PYTEST) $(PYTEST_OPTIONS) ; \
        fi ; \
        cd -

# openhardwaremonitor cannot be built in parallel, ensure non-parallel with -j1:
openhardwaremonitor:
	$(MAKE) -j1 -C $(bindir)/../../omd/packages/openhardwaremonitor dist

# Force regeneration of coverage data during test run.
coverage-reset:
	rm -fr "*coverage.info"
	find . -name "*.gcda" -delete
	lcov --directory . --zerocounters

coverage.info: WindowsAgentCoverage$(EXEEXT) coverage-reset
	DISPLAY="$$DISPLAY xterm" wine $< 2>/dev/null ; \
        lcov -c --rc lcov_branch_coverage=1 --directory . -o $@

filtered_coverage.info: coverage.info
	lcov --rc lcov_branch_coverage=1 --remove $< "/usr/*" "c++/*" -o $@

unittest-coverage-html: filtered_coverage.info
	genhtml $< --rc lcov_branch_coverage=1 -o htmlcov
