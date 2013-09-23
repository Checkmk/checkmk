# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

Summary:   Nagios agent and check plugin by Mathias Kettner for efficient remote monitoring
Name:      check_mk
Version:   (automatically inserted)
Release:   1
License:   GPL
Group:     System/Monitoring
URL:       http://mathias-kettner.de/check_mk
Source:    check_mk-%{version}.tar.gz
BuildRoot: /tmp/rpm.buildroot.check_mk-%{version}
AutoReq:   off
AutoProv:  off
BuildArch: noarch


%description
check_mk is a xinetd-based remote agent for monitoring Linux and Unix-Servers
with Nagios plus a Check-Plugin check_mk written in Python.
This package is only needed on the Nagios server.

%package agent
Group:     System/Monitoring
Requires:  xinetd, time
Summary: Linux-Agent for check_mk
AutoReq:   off
AutoProv:  off
Conflicts: check_mk-caching-agent check_mk-agent-scriptless
%description agent
This package contains the agent for check_mk. Install this on
all Linux machines you want to monitor via check_mk. You'll need
xinetd to run this agent.

%package agent-scriptless
Group:     System/Monitoring
Requires:  xinetd, time
Summary: Linux-Agent for check_mk
AutoReq:   off
AutoProv:  off
Conflicts: check_mk-caching-agent check_mk-agent
%description agent-scriptless
This package contains the agent for check_mk. Install this on
all Linux machines you want to monitor via check_mk. You'll need
xinetd to run this agent. This package does not run any scripts during
installation. You will need to manage the xinetd configuration on your
own.

%package caching-agent
Group:     System/Monitoring
Requires:  xinetd, time
Summary: Caching Linux-Agent for check_mk
AutoReq:   off
AutoProv:  off
Conflicts: check_mk-agent agent-scriptless
%description caching-agent
This package contains the agent for check_mk with an xinetd
configuration that wrap the agent with the check_mk_caching_agent
wrapper. Use it when doing fully redundant monitoring, where
an agent is regularily polled by more than one monitoring
server.

%package agent-logwatch
Group:     System/Monitoring
Requires:  check_mk-agent, python
Summary: Logwatch-Plugin for check_mk agent
AutoReq:   off
AutoProv:  off
%description agent-logwatch
The logwatch plugin for the check_mk agent allows you to monitor
logfiles on Linux and UNIX. In one or more configuration files you
specify patters for log messages that should raise a warning or
critical state. For each logfile the current position is remembered.
This way only new messages are being sent.

%package agent-oracle
Group:     System/Monitoring
Requires:  check_mk-agent
Summary: ORACLE-Plugin for check_mk agent
AutoReq:   off
AutoProv:  off
%description agent-oracle
The ORACLE plugin for the check_mk agent allows you to monitor
several aspects of ORACLE databases. You need to adapt the
script /etc/check_mk/sqlplus.sh to your needs.

%package web
Group:     System/Monitoring
Requires:  python
Summary: Check_mk web pages
AutoReq:   off
AutoProv:  off
%description web
This package contains the Check_mk webpages. They allow you to
search for services and apply Nagios commands to the search results.

%prep
%setup -q

%install
R=$RPM_BUILD_ROOT
rm -rf $R
DESTDIR=$R ./setup.sh --yes
rm -vf $R/etc/check_mk/*.mk-*

# install agent
mkdir -p $R/etc/xinetd.d
mkdir -p $R/usr/share/doc/check_mk_agent
install -m 644 COPYING ChangeLog AUTHORS $R/usr/share/doc/check_mk_agent
install -m 644 $R/usr/share/check_mk/agents/xinetd.conf $R/etc/xinetd.d/check_mk
install -m 644 $R/usr/share/check_mk/agents/xinetd_caching.conf $R/etc/xinetd.d/check_mk_caching
mkdir -p $R/usr/bin
install -m 755 $R/usr/share/check_mk/agents/check_mk_agent.linux $R/usr/bin/check_mk_agent
install -m 755 $R/usr/share/check_mk/agents/check_mk_caching_agent.linux $R/usr/bin/check_mk_caching_agent
install -m 755 $R/usr/share/check_mk/agents/waitmax $R/usr/bin
install -m 755 $R/usr/share/check_mk/agents/mk-job $R/usr/bin
mkdir -p $R/usr/lib/check_mk_agent/plugins
mkdir -p $R/usr/lib/check_mk_agent/local
mkdir -p $R/var/lib/check_mk_agent
mkdir -p $R/var/lib/check_mk_agent/job

# logwatch and oracle extension
install -m 755 $R/usr/share/check_mk/agents/plugins/mk_logwatch $R/usr/lib/check_mk_agent/plugins
install -m 755 $R/usr/share/check_mk/agents/plugins/mk_oracle $R/usr/lib/check_mk_agent/plugins
install -m 644 $R/usr/share/check_mk/agents/logwatch.cfg $R/etc/check_mk
install -m 755 $R/usr/share/check_mk/agents/sqlplus.sh   $R/etc/check_mk

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
%config(noreplace) /etc/check_mk/main.mk
%config(noreplace) /etc/check_mk/multisite.mk
/etc/check_mk/conf.d/README
%config(noreplace) /etc/nagios/objects/*
/usr/bin/check_mk
/usr/bin/cmk
/usr/bin/mkp
%dir /usr/share/check_mk
/usr/share/check_mk/agents
/usr/share/check_mk/checks
/usr/share/check_mk/notifications
/usr/share/check_mk/modules
/usr/share/check_mk/pnp-templates/*
/usr/share/check_mk/check_mk_templates.cfg
/usr/share/doc/check_mk
%dir /var/lib/check_mk
%dir %attr(-,nagios,root) /var/lib/check_mk/counters
%dir %attr(-,nagios,root) /var/lib/check_mk/cache
%dir %attr(-,nagios,root) /var/lib/check_mk/logwatch
%dir /var/lib/check_mk/autochecks
%dir /var/lib/check_mk/precompiled
%dir /var/lib/check_mk/packages
/var/lib/check_mk/packages/check_mk

# Spaeter Subpaket draus machen
/usr/bin/unixcat
/usr/lib/check_mk/livestatus.o
/usr/lib/check_mk/livecheck

%files agent
%config(noreplace) /etc/xinetd.d/check_mk
/usr/bin/check_mk_agent
/usr/bin/waitmax
/usr/bin/mk-job
/usr/share/doc/check_mk_agent
%dir /usr/lib/check_mk_agent/local
%dir /usr/lib/check_mk_agent/plugins
%dir /var/lib/check_mk_agent
%dir %attr(1777,-,-)/var/lib/check_mk_agent/job

%files agent-scriptless
%config(noreplace) /etc/xinetd.d/check_mk
/usr/bin/check_mk_agent
/usr/bin/waitmax
/usr/bin/mk-job
/usr/share/doc/check_mk_agent
%dir /usr/lib/check_mk_agent/local
%dir /usr/lib/check_mk_agent/plugins
%dir /var/lib/check_mk_agent
%dir %attr(1777,-,-)/var/lib/check_mk_agent/job

%files caching-agent
%config(noreplace) /etc/xinetd.d/check_mk_caching
/usr/bin/check_mk_agent
/usr/bin/check_mk_caching_agent
/usr/bin/waitmax
/usr/bin/mk-job
/usr/share/doc/check_mk_agent
%dir /usr/lib/check_mk_agent/local
%dir /usr/lib/check_mk_agent/plugins
%dir /etc/check_mk
%dir /var/lib/check_mk_agent
%dir %attr(1777,-,-)/var/lib/check_mk_agent/job

%files agent-logwatch
/usr/lib/check_mk_agent/plugins/mk_logwatch
%config(noreplace) /etc/check_mk/logwatch.cfg

%files agent-oracle
/usr/lib/check_mk_agent/plugins/mk_oracle
%config(noreplace) /etc/check_mk/sqlplus.sh

%files web
/usr/share/check_mk/web
%config(noreplace) /etc/apache2/conf.d/*

%pre
# Make sure user 'nagios' exists
RUNUSER=nagios
if ! id $RUNUSER > /dev/null 2>&1
then
    useradd -r -c 'Nagios' -d /var/lib/nagios nagios
    echo "Created user nagios"
fi

%define reload_xinetd if [ -x /etc/init.d/xinetd ] ; then if pgrep -x xinetd >/dev/null ; then echo "Reloading xinetd..." ; /etc/init.d/xinetd reload ; else echo "Starting xinetd..." ; /etc/init.d/xinetd start ; fi ; fi

%define activate_xinetd if which chkconfig >/dev/null 2>&1 ; then echo "Activating startscript of xinetd" ; chkconfig xinetd on ; fi

%pre agent
if [ ! -x /etc/init.d/xinetd ] ; then
    echo
    echo "---------------------------------------------"
    echo "WARNING"
    echo
    echo "This package needs xinetd to be installed. "
    echo "Currently you do not have installed xinetd. "
    echo "Please install and start xinetd or install "
    echo "and setup another inetd manually."
    echo ""
    echo "It's also possible to monitor via SSH without "
    echo "an inetd."
    echo "---------------------------------------------"
    echo
fi

%post agent
%activate_xinetd
%reload_xinetd

%postun agent
%reload_xinetd

# Sorry. I need to copy&paste all scripts from the normal agent to 
# the caching agent. This might better be done with RPM macros. But
# that are very ugly if you want to do multi line shell scripts...
%pre caching-agent
if [ ! -x /etc/init.d/xinetd ] ; then
    echo
    echo "---------------------------------------------"
    echo "WARNING"
    echo
    echo "This package needs xinetd to be installed. "
    echo "Currently you do not have installed xinetd. "
    echo "Please install and start xinetd or install "
    echo "and setup another inetd manually."
    echo ""
    echo "It's also possible to monitor via SSH without "
    echo "an inetd."
    echo "---------------------------------------------"
    echo
fi

%post caching-agent
%activate_xinetd
%reload_xinetd

%postun caching-agent
%reload_xinetd

