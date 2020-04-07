# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

Summary:   Checkmk Agent for Linux
Name:      check-mk-agent
Version:   (automatically inserted)
Release:   1
License:   GPL
Group:     System/Monitoring
URL:       https://checkmk.com/
Vendor:    tribe29 GmbH
Source:    check-mk-agent-%{_version}.tar.gz
BuildRoot: %{_topdir}/buildroot
AutoReq:   off
AutoProv:  off
BuildArch: noarch
Obsoletes: check_mk-agent check_mk_agent
Provides:  check_mk-agent check_mk_agent

%description
The Checkmk Agent uses xinetd or systemd to provide information about the system
on TCP port 6556. This can be used to monitor the host via Checkmk.

%define _binaries_in_noarch_packages_terminate_build 0

%prep
%setup -n check-mk-agent-%{_version}

%install

R=$RPM_BUILD_ROOT
rm -rf $R

# install agent
# xinitd
mkdir -p $R/etc/xinetd.d
install -m 644 cfg_examples/xinetd.conf $R/etc/xinetd.d/check_mk
# Systemd
mkdir -p $R/etc/systemd/system
install -m 644 cfg_examples/systemd/check_mk\@.service $R/etc/systemd/system
install -m 644 cfg_examples/systemd/check_mk.socket $R/etc/systemd/system
mkdir -p $R/etc/check_mk
mkdir -p $R/usr/bin
install -m 755 check_mk_agent.linux $R/usr/bin/check_mk_agent
install -m 755 check_mk_caching_agent.linux $R/usr/bin/check_mk_caching_agent
install -m 755 waitmax $R/usr/bin
install -m 755 mk-job $R/usr/bin
mkdir -p $R/usr/lib/check_mk_agent/plugins
mkdir -p $R/usr/lib/check_mk_agent/local
mkdir -p $R/var/lib/check_mk_agent
mkdir -p $R/var/lib/check_mk_agent/job
mkdir -p $R/var/lib/check_mk_agent/spool

%clean
rm -rf $RPM_BUILD_ROOT

%files
%config(noreplace) /etc/xinetd.d/check_mk
%config(noreplace) /etc/systemd/system/check_mk@.service
%config(noreplace) /etc/systemd/system/check_mk.socket
/etc/check_mk
/usr/bin/*
/usr/lib/check_mk_agent
/var/lib/check_mk_agent

%define reload_xinetd if which xinetd >/dev/null 2>&1 && ! which systemctl >/dev/null 2>&1 ; then if pgrep -x xinetd >/dev/null ; then echo "Reloading xinetd..." ; service xinetd reload ; else echo "Starting xinetd..." ; service xinetd start ; fi ; fi

%define activate_xinetd if which xinetd >/dev/null 2>&1 && which chkconfig >/dev/null 2>&1 ; then echo "Activating startscript of xinetd" ; chkconfig xinetd on ; fi

%define cleanup_rpmnew if [ -f /etc/xinetd.d/check_mk.rpmnew ] ; then rm /etc/xinetd.d/check_mk.rpmnew ; fi

%define systemd_enable if which systemctl >/dev/null 2>&1 ; then echo "Enable Checkmk Agent in systemd..." ; sed -i 's/\(disable[^=]*= \).*/\1yes/g' /etc/xinetd.d/check_mk ; systemctl enable check_mk.socket ; systemctl restart sockets.target ; fi

%pre
if ! which xinetd >/dev/null 2>&1 && ! which systemctl >/dev/null 2>&1 ; then
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

%post
%cleanup_rpmnew
%activate_xinetd
%reload_xinetd
%systemd_enable

%postun
%reload_xinetd
