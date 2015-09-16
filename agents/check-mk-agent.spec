# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
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

Summary:   Check_MK Agent for Linux
Name:      check-mk-agent
Version:   (automatically inserted)
Release:   1
License:   GPL
Group:     System/Monitoring
URL:       http://mathias-kettner.de/check_mk.html
Source:    check-mk-agent-%{_version}.tar.gz
BuildRoot: %{_topdir}/buildroot
AutoReq:   off
AutoProv:  off
BuildArch: noarch
Obsoletes: check_mk-agent check_mk_agent

%description
The Check_MK Agent uses xinetd to provide information about the system
on TCP port 6556. This can be used to monitor the host via Check_MK.

%prep
%setup -n check-mk-agent-%{_version}

%install

R=$RPM_BUILD_ROOT
rm -rf $R

# install agent
# xinitd
mkdir -p $R/etc/xinetd.d
install -m 644 xinetd.conf $R/etc/xinetd.d/check_mk
# Systemd
mkdir -p $R/etc/systemd/system
install -m 644 systemd/check_mk\@.service $R/etc/systemd/system
install -m 644 systemd/check_mk.socket $R/etc/systemd/system
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

%define reload_xinetd if [ -x /etc/init.d/xinetd ] ; then if pgrep -x xinetd >/dev/null ; then echo "Reloading xinetd..." ; /etc/init.d/xinetd reload ; else echo "Starting xinetd..." ; /etc/init.d/xinetd start ; fi ; fi

%define reload_xinetd_systemd if [ ! -x /etc/init.d/xinetd ] && [ -x /usr/sbin/xinetd ]; then if pgrep -x xinetd >/dev/null ; then echo "Reloading xinetd..." ; service xinetd reload ; else echo "Starting xinetd..." ; service init.d/xinetd start ; fi ; fi

%define activate_xinetd if [ -x /usr/bin/xinetd ] && [ which chkconfig >/dev/null 2>&1 ] ; then echo "Activating startscript of xinetd" ; chkconfig xinetd on ; fi
%define cleanup_rpmnew if [ -f /etc/xinetd.d/check_mk.rpmnew ] ; then rm /etc/xinetd.d/check_mk.rpmnew ; fi

%define systemd_enable if [ -x /usr/bin/systemctl ] && [ ! -x /usr/sbin/xinetd ] ; then echo "Enable Check_MK_Agent in systemd..." ; systemctl enable check_mk.socket ; systemctl restart sockets.target ; fi

%pre
if [ ! -x /usr/sbin/xinetd ] && [ ! -x /usr/bin/systemctl ] ; then
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
%reload_xinetd_systemd
%systemd_enable

%postun
%reload_xinetd
