#!/bin/bash
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2009             mk@mathias-kettner.de |
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

# Make sure, /usr/local/bin is in the PATH, since we install
# programs there...
PATH=$PATH:/usr/local/bin

set -e

NAGIOS_VERSION=3.2.0
PLUGINS_VERSION=1.4.14
CHECK_MK_VERSION=1.1.2rc1
PNP_VERSION=0.4.2
PNP_NAME=pnp
NAGVIS_VERSION=1.4.5
RRDTOOL_VERSION=1.4.2

SOURCEFORGE_MIRROR=dfn
NAGIOS_URL="http://downloads.sourceforge.net/project/nagios/nagios-3.x/nagios-$NAGIOS_VERSION/nagios-$NAGIOS_VERSION.tar.gz?use_mirror=$SOURCEFORGE_MIRROR"
PLUGINS_URL="http://downloads.sourceforge.net/project/nagiosplug/nagiosplug/$PLUGINS_VERSION/nagios-plugins-$PLUGINS_VERSION.tar.gz?use_mirror=$SOURCEFORGE_MIRROR"
CHECK_MK_URL="http://mathias-kettner.de/download/check_mk-$CHECK_MK_VERSION.tar.gz"
NAGVIS_URL="http://downloads.sourceforge.net/project/nagvis/NagVis%201.4%20%28stable%29/NagVis-$NAGVIS_VERSION/nagvis-$NAGVIS_VERSION.tar.gz?use_mirror=$SOURCEFORGE_MIRROR"
if [ "${PNP_VERSION:2:1}" = 6 ]
then
   PNP_URL="http://downloads.sourceforge.net/project/pnp4nagios/PNP-${PNP_VERSION:0:3}/pnp4nagios-$PNP_VERSION.tar.gz?use_mirror=$SOURCEFORGE_MIRROR"
   PNP_DATAOPTION=--datarootdir=/usr/local/share/nagios/htdocs/pnp
else
   PNP_URL="http://downloads.sourceforge.net/project/pnp4nagios/PNP/pnp-${PNP_VERSION}/pnp-${PNP_VERSION}.tar.gz?use_mirror=$SOURCEFORGE_MIRROR"
   PNP_DATAOPTION=--datadir=/usr/local/share/nagios/htdocs/pnp
fi

RRDTOOL_URL="http://oss.oetiker.ch/rrdtool/pub/rrdtool-$RRDTOOL_VERSION.tar.gz"

if [ "$(cat /etc/redhat-release 2>/dev/null)" = "Red Hat Enterprise Linux Server release 5.3 (Tikanga)" ]
then
    DISTRO=REDHAT
    DISTRONAME="RedHat 5.3"
    DISTROVERS=5.3
elif [ "$(cat /etc/redhat-release 2>/dev/null)" = "CentOS release 5.3 (Final)" ]
then
    DISTRO=REDHAT
    DISTRONAME="CentOS 5.3"
    DISTROVERS=5.3
else
    DISTRO=DEBIAN
    DISTRONAME="Debian 5.0 (Lenny)"
    DISTROVERS=5.0
    WWWUSER=www-data
fi

if [ "$DISTRO" = REDHAT  -o "$DISTRO" = SUSE ]
then
    HTTPD=httpd
    WWWUSER=apache
    activate_initd () 
    {
        chkconfig $1 on
    }
else
    HTTPD=apache2
    activate_initd ()
    {
	update-rc.d $1 defaults
    }
fi



cat <<EOF

This script is intended for setting up Nagios, PNP4Nagios and
check_mk on a freshly installed Linux system.

 - probably delete your existing Nagios configuration (if any)
 - install missing packages from Debian sources via aptitude
 - download software from various internet sources
 - compile Nagios and PNP4Nagios
 - install everything into FHS-compliant paths below /etc,
   /var and /usr/local
 - setup Nagios, Apache, PNP4Nagios and check_mk
 - install the check_mk_agent on localhost
 - setup Nagios to monitor localhost

   You Linux distro:     $DISTRONAME
   Nagios version:       $NAGIOS_VERSION
   Plugins version:      $PLUGINS_VERSION
   Check_MK version:     $CHECK_MK_VERSION
   rrdtool version:      $RRDTOOL_VERSION
   PNP4Nagios version:   $PNP_VERSION
   Nagvis version:       $NAGVIS_VERSION

No user interaction is neccesary. Do you want to proceed?
EOF

echo -n 'Then please enter "yes": '
read yes
[ "$yes" = yes ] || exit 0

set -e

if [ "$DISTRO" = DEBIAN ]
then
  aptitude -y update
  aptitude -y install psmisc build-essential nail nagios-plugins-basic \
    apache2 libapache2-mod-php5 python rrdtool php5-gd libgd-dev \
    python-rrdtool xinetd wget libgd2-xpm-dev psmisc less libapache2-mod-python \
    graphviz php5-sqlite sqlite php-gettext locales-all
    # Hint for Debian: Installing the packages locales-all is normally not neccessary
    # if you use 'dpkg-reconfigure locales' to setup and generate your locales.
    # Correct locales are needed for the localisation of Nagvis.
else
   yum update
   yum -y install httpd gcc mailx php php-gd gd-devl xinetd wget psmisc less mod_python \
     sqlite cairo-devel libxml2-devel pango-devel pango libpng-devel freetype freetype-devel libart_lgpl-devel 
   true
fi

set +e
killall nagios
killall -9 nagios
killall npcd
set -e

# Compile rrdtool
[ -e rrdtool-$RRDTOOL_VERSION ] || wget $RRDTOOL_URL
rm -rf rrdtool-$RRDTOOL_VERSION
tar xzf rrdtool-$RRDTOOL_VERSION.tar.gz
pushd rrdtool-$RRDTOOL_VERSION
./configure --prefix=/usr/local
make -j 16
make DESTDIR=$DESTDIR install
popd


# Compile plugins
[ -e nagios-plugins-$PLUGINS_VERSION.tar.gz ] || wget $PLUGINS_URL
rm -rf nagios-plugins-$PLUGINS_VERSION
tar xzf nagios-plugins-$PLUGINS_VERSION.tar.gz
pushd nagios-plugins-$PLUGINS_VERSION
./configure \
  --libexecdir=/usr/local/lib/nagios/plugins
make -j 16
make DESTDIR=$DESTDIR install
popd

# Compile Nagios
[ -e nagios-$NAGIOS_VERSION.tar.gz ] || wget $NAGIOS_URL
rm -rf nagios-$NAGIOS_VERSION
tar xzf nagios-$NAGIOS_VERSION.tar.gz
pushd nagios-$NAGIOS_VERSION
groupadd -r nagios >/dev/null 2>&1 || true
id nagios >/dev/null 2>&1 || useradd -c 'Nagios Daemon' -s /bin/false -d /var/lib/nagios -r -g nagios nagios
./configure \
  --with-nagios-user=nagios \
  --with-nagios-group=nagios \
  --with-command-user=$WWWUSER \
  --with-command-group=nagios \
  --with-mail=mail \
  --with-httpd-conf=/etc/nagios \
  --with-checkresult-dir=/var/spool/nagios/checkresults \
  --with-temp-dir=/var/lib/nagios/tmp \
  --with-init-dir=/etc/init.d \
  --with-lockfile=/var/run/nagios.lock \
  --with-cgiurl=/nagios/cgi-bin \
  --with-htmurl=/nagios \
  --bindir=/usr/local/bin \
  --sbindir=/usr/local/lib/nagios/cgi-bin \
  --libexecdir=/usr/local/lib/nagios \
  --sysconfdir=/etc/nagios \
  --sharedstatedir=/var/lib/nagios \
  --localstatedir=/var/lib/nagios \
  --libdir=/usr/local/lib/nagios \
  --includedir=/usr/local/include/nagios \
  --datadir=/usr/local/share/nagios/htdocs \
  --disable-statuswrl \
  --enable-nanosleep \
  --enable-event-broker \
  --disable-embedded-perl

make -j 16 all

make DESTDIR=$DESTDIR \
  install \
  install-cgis \
  install-html \
  install-init \
  install-commandmode \
  install-config 

chown -R root.root \
  $DESTDIR/usr/local/bin/nagios* \
  $DESTDIR/usr/local/*/nagios \
  $DESTDIR/etc/nagios

sed -i '/CONFIG ERROR/a\                        $NagiosBin -v $NagiosCfgFile'  $DESTDIR/etc/init.d/nagios


mkdir -p $DESTDIR/var/lib/nagios/tmp
chown -R nagios.nagios $DESTDIR/var/lib/nagios
mkdir -p $DESTDIR/var/log/nagios
chown nagios.nagios $DESTDIR/var/log/nagios
mkdir -p $DESTDIR/var/cache/nagios
chown nagios.nagios $DESTDIR/var/cache/nagios
mkdir -p $DESTDIR/var/run/nagios/rw
chown nagios.nagios $DESTDIR/var/run/nagios/rw
chmod 2755 $DESTDIR/var/run/nagios/rw
mkdir -p  $DESTDIR/var/lib/nagios/rrd
chown nagios.nagios $DESTDIR/var/lib/nagios/rrd

chown root.nagios /usr/local/lib/nagios/plugins/check_icmp
chmod 4750 /usr/local/lib/nagios/plugins/check_icmp

# Prepare configuration
popd
pushd $DESTDIR/etc/nagios
mv nagios.cfg nagios.cfg-example
mv objects conf.d-example
: > resource.cfg
cat <<EOF > nagios.cfg
# Paths
lock_file=/var/run/nagios.lock
temp_file=/var/lib/nagios/nagios.tmp
temp_path=/var/lib/nagios/tmp
log_archive_path=/var/lib/nagios/archives
check_result_path=/var/spool/nagios/checkresults
state_retention_file=/var/lib/nagios/retention.dat
debug_file=/var/log/nagios/nagios.debug
command_file=/var/run/nagios/rw/nagios.cmd
log_file=/var/log/nagios/nagios.log
cfg_dir=/etc/nagios/conf.d
object_cache_file=/var/cache/nagios/objects.cache
precached_object_file=/var/cache/nagios/objects.precache
resource_file=/etc/nagios/resource.cfg
status_file=/var/lib/nagios/status.dat

# Logging
log_rotation_method=w
use_syslog=0
log_notifications=1
log_service_retries=0
log_host_retries=1
log_event_handlers=1
log_initial_states=0
log_external_commands=0
log_passive_checks=0

status_update_interval=10
nagios_user=nagios
nagios_group=nagios
check_external_commands=1
command_check_interval=-1
external_command_buffer_slots=4096
max_service_check_spread=1
max_host_check_spread=1
check_result_reaper_frequency=1
service_check_timeout=120
host_check_timeout=30
retain_state_information=1
retention_update_interval=60
use_retained_program_state=1
use_retained_scheduling_info=1
retained_host_attribute_mask=0
retained_service_attribute_mask=0
retained_process_host_attribute_mask=0
retained_process_service_attribute_mask=0
retained_contact_host_attribute_mask=0
retained_contact_service_attribute_mask=0
check_for_updates=0
process_performance_data=1
date_format=iso8601
enable_embedded_perl=0
use_regexp_matching=0
use_true_regexp_matching=0
use_large_installation_tweaks=1
enable_environment_macros=1
debug_level=0
debug_verbosity=0
max_debug_file_size=1000000

# PNP4Nagios
service_perfdata_command=process-service-perfdata
host_perfdata_command=process-host-perfdata

# Illegal characters
EOF

grep 'illegal.*=' nagios.cfg-example >> nagios.cfg

sed -i 's/_blank/main/g' cgi.cfg

mkdir -p conf.d
cat <<EOF > conf.d/timeperiods.cfg
define timeperiod {
        timeperiod_name 24x7
        alias           24 Hours A Day, 7 Days A Week
        sunday          00:00-24:00
        monday          00:00-24:00
        tuesday         00:00-24:00
        wednesday       00:00-24:00
        thursday        00:00-24:00
        friday          00:00-24:00
        saturday        00:00-24:00
}
EOF

cat <<EOF > conf.d/localhost.cfg
define contact {
   contact_name                  hh
   alias                         Harri Hirsch
   email                         ha@hirsch.de
   host_notification_commands    dummy
   service_notification_commands dummy
}

define contactgroup {
   contactgroup_name     admins
   alias                 All Admins
   members               hh
}

define hostgroup {
  hostgroup_name         all
  alias                  All Rechner
}

define host {
  host_name              nagios
  alias                  The Nagios Server
  hostgroups             all
  contact_groups         admins
  address                127.0.0.1
  max_check_attempts     1
  notification_interval  0
  check_command          check-icmp
}

define service {
  host_name              nagios
  check_command          dummy
  service_description    PING
  max_check_attempts     1
  normal_check_interval  1
  retry_check_interval   1
  notification_interval  0
}

define command {
  command_name dummy
  command_line echo 'OK - Dummy check, always true'
}

define command {
  command_name check-icmp
  command_line /usr/local/lib/nagios/plugins/check_icmp $HOSTADDRESS$
}

EOF

cat <<EOF > conf.d/pnp4nagios.cfg
define command {
   command_name  process-service-perfdata
   command_line  /usr/bin/perl /usr/local/lib/nagios/process_perfdata.pl
}

define command {
   command_name  process-host-perfdata
   command_line  /usr/bin/perl /usr/local/lib/nagios/process_perfdata.pl -d HOSTPERFDATA
}
EOF



echo 'nagiosadmin:vWQwFr7mwjvmI' > htpasswd


mkdir -p $DESTDIR/etc/$HTTPD/conf.d
ln -sfn /etc/nagios/$HTTPD.conf $DESTDIR/etc/$HTTPD/conf.d/nagios.conf

rm -rf conf.d-example

popd

# Compile and install PNP4Nagios
[ -e $PNP_NAME-$PNP_VERSION.tar.gz ] || wget "$PNP_URL"
tar xzf $PNP_NAME-$PNP_VERSION.tar.gz
pushd $PNP_NAME-$PNP_VERSION

./configure \
  --bindir=/usr/local/bin \
  --sbindir=/usr/local/lib/nagios/cgi-bin \
  --libexecdir=/usr/local/lib/nagios \
  --sysconfdir=/etc/nagios \
  --sharedstatedir=/var/lib/nagios \
  --localstatedir=/var/lib/nagios \
  --libdir=/usr/local/lib/nagios \
  --includedir=/usr/local/include/nagios \
  $PNP_DATAOPTION

make all
make DESTDIR=$DESTDIR install install-config
rm -rf $DESTDIR/etc/nagios/check_commands
popd
pushd $DESTDIR/etc/nagios
mv rra.cfg-sample rra.cfg
mv process_perfdata.cfg-sample process_perfdata.cfg
mv npcd.cfg-sample npcd.cfg
sed -i 's@^RRDPATH =.*@RRDPATH = /var/lib/nagios/rrd@' process_perfdata.cfg
sed -i 's@^\(.conf\[.rrdbase.\] =\).*@\1"/var/lib/nagios/rrd/";@' config.php
popd

# Und auch noch Nagvis
[ -e nagvis-$NAGVIS_VERSION.tar.gz ] || wget "$NAGVIS_URL"
rm -rf nagvis-$NAGVIS_VERSION
tar xzf nagvis-$NAGVIS_VERSION.tar.gz
pushd nagvis-$NAGVIS_VERSION
./install.sh -q -F -c y \
  -u $WWWUSER \
  -g $WWWUSER \
  -w /etc/$HTTPD/conf.d \
  -W /nagvis \
  -B /usr/local/bin/nagios \
  -b /usr/bin \
  -p /usr/local/nagvis \
  -B /usr/local/bin
popd

sed -i -e 's@^;socket="unix:.*@socket="unix:/var/run/nagios/rw/live"@' \
       -e 's@^;backend=.*@backend="live_1"@' \
   /usr/local/nagvis/etc/nagvis.ini.php

cat <<EOF > /etc/$HTTPD/conf.d/nagios.conf
Alias /nagvis/ /usr/local/nagvis/
<Directory /usr/local/nagvis/>
   allow from all
   AuthName "Nagios Monitoring"
   AuthType Basic
   AuthUserFile "/etc/nagios/htpasswd"
   require valid-user 
</Directory>

ScriptAlias /nagios/cgi-bin/ /usr/local/lib/nagios/cgi-bin/
<Directory /usr/local/lib/nagios/cgi-bin/>
   allow from all
   AuthName "Nagios Monitoring"
   AuthType Basic
   AuthUserFile "/etc/nagios/htpasswd"
   require valid-user 
</Directory>

Alias /nagios/ /usr/local/share/nagios/htdocs/
<Directory /usr/local/share/nagios/htdocs/>
   allow from all
   AuthName "Nagios Monitoring"
   AuthType Basic
   AuthUserFile "/etc/nagios/htpasswd"
   require valid-user 
</Directory>
EOF



gpasswd -a $WWWUSER nagios
/etc/init.d/$HTTPD stop
/etc/init.d/$HTTPD start
killall nagios || true
/etc/init.d/nagios start
activate_initd nagios || true

# check_mk
if [ ! -e check_mk-$CHECK_MK_VERSION.tar.gz ]
then
    wget "$CHECK_MK_URL"
fi
rm -rf check_mk-$CHECK_MK_VERSION
tar xzf check_mk-$CHECK_MK_VERSION.tar.gz
pushd check_mk-$CHECK_MK_VERSION
rm -f ~/.check_mk_setup.conf
rm -rf /var/lib/check_mk /etc/check_mk

# Set some non-default paths which cannot be 
# autodetected
cat <<EOF > ~/.check_mk_setup.conf 
check_icmp_path='/usr/local/lib/nagios/plugins/check_icmp'
EOF

DESTDIR=$DESTDIR ./setup.sh --yes
echo 'do_rrd_update = False' >> /etc/check_mk/main.mk
popd

# Apache neu starten
/etc/init.d/$HTTPD restart
activate_initd httpd

# side.html anpassen
HTML='<div class="navsectiontitle">Check_MK</div><div class="navsectionlinks"><ul class="navsectionlinks"><li><a href="/check_mk/filter.py" target="<?php echo $link_target;?>">Filters and Actions</a></li></div></div><div class="navsection"><div class="navsectiontitle">Nagvis</div><div class="navsectionlinks"><ul class="navsectionlinks"><li><a href="/nagios/nagvis/" target="<?php echo $link_target;?>">Overview page</a></li></div></div><div class="navsection">'
QUOTE=${HTML//\//\\/}
sed -i "/.*Reports<.*$/i$QUOTE" /usr/local/share/nagios/htdocs/side.php

# Agent fuer localhost
mkdir -p $DESTDIR/etc/xinetd.d
cp $DESTDIR/usr/share/check_mk/agents/xinetd.conf $DESTDIR/etc/xinetd.d/check_mk
mkdir -p $DESTDIR/usr/bin
install -m 755 $DESTDIR/usr/share/check_mk/agents/check_mk_agent.linux $DESTDIR/usr/bin/check_mk_agent
/etc/init.d/xinetd stop || true
/etc/init.d/xinetd start
activate_initd xinetd

cat <<EOF > $DESTDIR/etc/check_mk/main.mk
all_hosts = [ 'localhost' ]
do_rrd_update = False
EOF
check_mk -I alltcp
rm $DESTDIR/etc/nagios/conf.d/localhost.cfg
check_mk -R



cat <<EOF

Nagios and the addons have been installed into the following paths:

 /etc/nagios              configuration of Nagios & PNP4Nagios
 /etc/check_mk            configuration of check_mk
 /etc/init.d/nagios       start script for Nagios

 /var/lib/nagios          data directory of Nagios
 /var/log/nagios          log files of Nagios
 /var/lib/check_mk        data directory of check_mk

 /usr/local               programs, scripts, fixed data

Now you can point your browser to to http://localhost/nagios/
and login with 'nagiosadmin' and 'test'.
You can change that password with
# htpasswd /etc/nagios/htpasswd nagiosadmin
EOF
