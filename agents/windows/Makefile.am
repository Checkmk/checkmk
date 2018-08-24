bin_PROGRAMS = check_mk_agent
check_PROGRAMS = WindowsAgentTest wmitest
noinst_LIBRARIES = libcheck_mk_agent.a
noinst_PROGRAMS = MontyPython

AUTOMAKE_OPTIONS = foreign
AM_CPPFLAGS = -I$(top_srcdir)/sections -O2 -Wformat=2 -Werror -Wall -fno-rtti \
              -std=c++17 -gdwarf-2 -DCHECK_MK_VERSION='"$(VERSION)"' \
              -D__USE_MINGW_ANSI_STDIO -DSI_SUPPORT_IOSTREAMS
AM_LDFLAGS = -static -static-libgcc -static-libstdc++
LD_COMMON = -lwsock32 -lws2_32 -lole32 -loleaut32 -lwbemuuid -lpsapi -lshlwapi -limagehlp -lstdc++fs

check_mk_agent_LDADD = check_mk_agent.res libcheck_mk_agent.a $(LD_COMMON)

WindowsAgentTest_CPPFLAGS = $(AM_CPPFLAGS) -I$(top_srcdir)/test
WindowsAgentTest_LDADD = libcheck_mk_agent.a -lgtest -lgmock $(LD_COMMON)

wmitest_LDADD = $(LD_COMMON)

pytest = /usr/bin/env pytest
pytest_options = --maxfail=10
pytest_jenkins = $(pytest_options) --junitxml=$(bindir)/junit.xml

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
unittest: WindowsAgentTest$(EXEEXT)
	TERM=linux DISPLAY="$$DISPLAY xterm" wine WindowsAgentTest$(EXEEXT)
#	DISPLAY="$$DISPLAY xterm" wine WindowsAgentTest$(EXEEXT) 2>/dev/null

integrationtest: install-strip openhardwaremonitor
	cd $(bindir)/it ; \
        rm -f remote.pyc ; \
        rm -rf __pycache__ ; \
        if [[ $$USER == jenkins ]] ; then \
          $(pytest) $(pytest_jenkins) ; \
        else \
          $(pytest) $(pytest_options) ; \
        fi ; \
        cd -

# openhardwaremonitor cannot be built in parallel, ensure non-parallel with -j1:
openhardwaremonitor:
	$(MAKE) -j1 -C $(bindir)/../../omd/packages/openhardwaremonitor dist

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

wmitest_SOURCES = Logger.cc WinApi.cc stringutil.cc wmiHelper.cc wmitest.cc

CLEANFILES = \
        *.ico *.res *.rc config.* stamp-* Makefile \
        $$(find . -name .dirstamp) \
        $$(find .deps/ sections/.deps test/.deps test/sections/.deps it/.deps -type f) \
        $(addprefix $(bindir)/,$(bin_PROGRAMS)) \
        $(patsubst %$(EXEEXT),%-64$(EXEEXT),$(addprefix $(bindir)/,$(bin_PROGRAMS))) \
        $(patsubst %$(EXEEXT),%.msi,$(addprefix $(bindir)/,$(bin_PROGRAMS)))
