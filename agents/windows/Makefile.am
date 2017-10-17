bin_PROGRAMS = check_mk_agent
check_PROGRAMS = WindowsAgentTest wmitest

AUTOMAKE_OPTIONS = foreign
AM_CPPFLAGS = -O2 -Wformat=2 -Werror -Wall -fno-rtti -std=c++14 -gdwarf-2 \
              -DCHECK_MK_VERSION='"$(VERSION)"' -D__USE_MINGW_ANSI_STDIO
AM_LDFLAGS = -static -static-libgcc -static-libstdc++
LD_COMMON = -lwsock32 -lws2_32 -lole32 -loleaut32 -lwbemuuid -lpsapi -lshlwapi -limagehlp -lntdll

check_mk_agent_LDADD = check_mk_agent.res $(LD_COMMON)

WindowsAgentTest_LDADD = -lgtest -lgmock

wmitest_LDADD = $(LD_COMMON)

build_version: $(check_mk_agent_SOURCES:.cc=.o)
	echo $$(( $$(cat $(VPATH)/build_version) + 1 )) > $(VPATH)/build_version

check_mk_agent.rc: $(VPATH)/check_mk_agent.rc.in build_version
	sed -e "s/%VERSION%/$(VERSION)/g" \
	    -e "s/%YEAR%/$$(date +%Y)/g" \
	    -e "s/%BUILD_VERSION%/$$(cat $(VPATH)/build_version)/g" $< > $@

check_mk_agent.res: check_mk_agent.rc $(VPATH)/check_mk_agent.ico
	cp $(VPATH)/check_mk_agent.ico check_mk_agent.ico
	$(WINDRES) $< -O coff -o $@

# Wine seems to depend on X Window authorization. Quiet "No protocol specified"
# warning by setting the DISPLAY variable accordingly.
unittest: WindowsAgentTest$(EXEEXT)
	DISPLAY="$$DISPLAY xterm" wine WindowsAgentTest$(EXEEXT)

check_mk_agent_SOURCES = \
        Configurable.cc \
        Configuration.cc \
        CrashHandler.cc \
        Crypto.cc \
        Environment.cc \
        EventLog.cc \
        EventLogVista.cc \
        ExternalCmd.cc \
        IEventLog.cc \
        ListenSocket.cc \
        Logger.cc \
        OHMMonitor.cc \
        OutputProxy.cc \
        PerfCounter.cc \
        PerfCounterCommon.cc \
        RotatingFileHandler.cc \
        Section.cc \
        SectionManager.cc \
        SettingsCollector.cc \
        Thread.cc \
        WinApi.cc \
        check_mk_agent.cc \
        stringutil.cc \
        types.cc \
        win_error.cc \
        wmiHelper.cc \
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

WindowsAgentTest_SOURCES = \
        Environment.cc \
        Logger.cc \
        win_error.cc \
        test/EnvironmentTest.cc \
        test/MockLogger.cc \
        test/MockWinApi.cc \
        test/gtest_main.cc

wmitest_SOURCES = wmitest.cc stringutil.cc WinApi.cc wmiHelper.cc

CLEANFILES = \
        *.ico *.res *.rc config.* stamp-* Makefile \
        sections/.dirstamp \
        $$(find .deps/ sections/.deps -type f) \
        $(addprefix $(bindir)/,$(bin_PROGRAMS)) \
        $(patsubst %$(EXEEXT),%-64$(EXEEXT),$(addprefix $(bindir)/,$(bin_PROGRAMS))) \
        $(patsubst %$(EXEEXT),%.msi,$(addprefix $(bindir)/,$(bin_PROGRAMS)))

setversion:
	package="Check_MK Windows Agent" ; \
	mail=feedback@check-mk.org ; \
	sed -i "s/^AC_INIT.*/AC_INIT([$$package], [$(NEW_VERSION)], [$$mail])/" \
	    $(VPATH)/configure.ac
