include ../../Makefile.omd

NAME         = openhardwaremonitor
VERSION      = 0.8.0
DIR          = openhardwaremonitor-$(VERSION)

.PHONY: build install skel clean

# c# project, requires mono to build

build: clean
	if [ -x "`which xbuild`" ] ; then \
	  unzip -d . $(DIR).zip ; \
	  cp -R OpenHardwareMonitorCLI OpenHardwareMonitor.sln $(DIR) ; \
	  xbuild /p:Configuration=Release $(DIR)/OpenHardwareMonitor.sln /target:OpenHardwareMonitorCLI ; \
	fi

install:
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/check_mk/agents/windows/ohm
	install -m 755 $(DIR)/Bin/Release/OpenHardwareMonitorCLI.exe $(DESTDIR)$(OMD_ROOT)/share/check_mk/agents/windows/ohm
	install -m 755 $(DIR)/Bin/Release/OpenHardwareMonitorLib.dll $(DESTDIR)$(OMD_ROOT)/share/check_mk/agents/windows/ohm

skel:

clean:
	if [ -x "`which xbuild`" ] ; then \
	  rm -rf $(DIR) ; \
	fi
