OPENHARDWAREMONITOR := openhardwaremonitor
OPENHARDWAREMONITOR_VERS := 0.8.0
OPENHARDWAREMONITOR_DIR := $(OPENHARDWAREMONITOR)-$(OPENHARDWAREMONITOR_VERS)

OPENHARDWAREMONITOR_INSTALL := $(BUILD_HELPER_DIR)/$(OPENHARDWAREMONITOR_DIR)-install
OPENHARDWAREMONITOR_UNPACK := $(BUILD_HELPER_DIR)/$(OPENHARDWAREMONITOR_DIR)-unpack

.PHONY: $(OPENHARDWAREMONITOR) $(OPENHARDWAREMONITOR)-setup $(OPENHARDWAREMONITOR)-clean-ohm $(OPENHARDWAREMONITOR)-dist $(OPENHARDWAREMONITOR)-build $(OPENHARDWAREMONITOR)-install $(OPENHARDWAREMONITOR)-skel $(OPENHARDWAREMONITOR)-clean

# This package can not, because it's a Mono project, and should not be built, because we compile
# a linux distro independent windows binary, during packaging procedure in the context of the
# single linux distributions. Instead we build the exe file during src/ packaging phase on our
# development server. This is equal to the precompiled windows agent and the agent updater.
$(OPENHARDWAREMONITOR):

$(OPENHARDWAREMONITOR)-install: $(OPENHARDWAREMONITOR_INSTALL)

# OpenHardwareMonitorCLI.exe OpenHardwareMonitorLib.dll: $(OPENHARDWAREMONITOR_DIR)/Bin/Release/OpenHardwareMonitorCLI.exe $(OPENHARDWAREMONITOR_DIR)/Bin/Release/OpenHardwareMonitorLib.dll
#	cp -p $(OPENHARDWAREMONITOR_DIR)/Bin/Release/OpenHardwareMonitorCLI.exe  \
#	      $(OPENHARDWAREMONITOR_DIR)/Bin/Release/OpenHardwareMonitorLib.dll \
#	      .

#$(OPENHARDWAREMONITOR_DIR)/Bin/Release/OpenHardwareMonitorCLI.exe $(OPENHARDWAREMONITOR_DIR)/Bin/Release/OpenHardwareMonitorLib.dll:  $(OPENHARDWAREMONITOR_UNPACK) $(OPENHARDWAREMONITOR_DIR)/OpenHardwareMonitorCLI $(OPENHARDWAREMONITOR_DIR)/OpenHardwareMonitor.sln
OpenHardwareMonitorCLI.exe OpenHardwareMonitorLib.dll:  $(OPENHARDWAREMONITOR_UNPACK) $(OPENHARDWAREMONITOR_DIR)/OpenHardwareMonitorCLI $(OPENHARDWAREMONITOR_DIR)/OpenHardwareMonitor.sln
# The strange "cat" below is necessary because the extremely ancient Mono
# versions coming with even the latest Ubuntus still contain the rather severe
# bug https://github.com/mono/mono/issues/6752. ("...System.Exception: Magic
# number is wrong: 542") :-P
	xbuild /p:Configuration=Release \
	       /p:TargetFrameworkVersion="v4.5" \
	       $(OPENHARDWAREMONITOR_DIR)/OpenHardwareMonitor.sln \
	       /target:OpenHardwareMonitorCLI | cat

$(OPENHARDWAREMONITOR_DIR)/OpenHardwareMonitorCLI: $(PACKAGE_DIR)/$(OPENHARDWAREMONITOR)/OpenHardwareMonitorCLI
	cp -r $< $(OPENHARDWAREMONITOR_DIR)/

$(OPENHARDWAREMONITOR_DIR)/OpenHardwareMonitor.sln: $(PACKAGE_DIR)/$(OPENHARDWAREMONITOR)/OpenHardwareMonitor.sln
	cp $<  $(OPENHARDWAREMONITOR_DIR)/

$(OPENHARDWAREMONITOR_INSTALL): OpenHardwareMonitorCLI.exe OpenHardwareMonitorLib.dll
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/check_mk/agents/windows/ohm
	install -m 755 OpenHardwareMonitorCLI.exe $(DESTDIR)$(OMD_ROOT)/share/check_mk/agents/windows/ohm
	install -m 755 OpenHardwareMonitorLib.dll $(DESTDIR)$(OMD_ROOT)/share/check_mk/agents/windows/ohm

$(OPENHARDWAREMONITOR)-skel:

# ToDo: Remove this from build scrtip.
$(OPENHARDWAREMONITOR)-setup:
	sudo apt-get install \
	    mono-complete \
	    mono-xbuild

$(OPENHARDWAREMONITOR)-dist: OpenHardwareMonitorCLI.exe OpenHardwareMonitorLib.dll

$(OPENHARDWAREMONITOR)-clean-ohm: clean
	rm -f OpenHardwareMonitorCLI.exe OpenHardwareMonitorLib.dll

$(OPENHARDWAREMONITOR)-clean:
	rm -rf $(OPENHARDWAREMONITOR_DIR) $(BUILD_HELPER_DIR)/$(OPENHARDWAREMONITOR_DIR)*
