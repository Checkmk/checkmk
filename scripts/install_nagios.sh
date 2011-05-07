#!/bin/bash
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2010             mk@mathias-kettner.de |
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

cat <<EOF

  NOTE
  ----------------------------------------------------------
  This is the last version of this script. There is a better
  alternative for installing and maintaining Nagios plus 
  Addons now:

  OMD - The Open Monitoring Distribution

  Please visit OMD at http://omdistro.org/

  OMD has been invented and founded by Mathias Kettner and is
  developed by a team of many well-known monitoring experts.
  ----------------------------------------------------------
  
Press enter to continue...
EOF
read



# Make sure, /usr/local/bin is in the PATH, since we install
# programs there...
PATH=$PATH:/usr/local/bin

LOGFILE=install_nagios.sh.log
exec > >(tee $LOGFILE) 2>&1

set -e

NAGIOS_VERSION=3.2.3
PLUGINS_VERSION=1.4.15
RRDTOOL_VERSION=1.4.4
CHECK_MK_VERSION=1.1.10p3
PNP_VERSION=0.6.6
NAGVIS_VERSION=1.5.6

SOURCEFORGE_MIRROR=dfn
NAGIOS_URL="http://downloads.sourceforge.net/project/nagios/nagios-3.x/nagios-$NAGIOS_VERSION/nagios-$NAGIOS_VERSION.tar.gz?use_mirror=$SOURCEFORGE_MIRROR"
PLUGINS_URL="http://downloads.sourceforge.net/project/nagiosplug/nagiosplug/$PLUGINS_VERSION/nagios-plugins-$PLUGINS_VERSION.tar.gz?use_mirror=$SOURCEFORGE_MIRROR"
CHECK_MK_URL="http://mathias-kettner.de/download/check_mk-$CHECK_MK_VERSION.tar.gz"
NAGVIS_URL="http://downloads.sourceforge.net/project/nagvis/NagVis%20${NAGVIS_VERSION:0:3}/nagvis-$NAGVIS_VERSION.tar.gz?use_mirror=$SOURCEFORGE_MIRROR"

PNP_URL="http://downloads.sourceforge.net/project/pnp4nagios/PNP-${PNP_VERSION:0:3}/pnp4nagios-$PNP_VERSION.tar.gz?use_mirror=$SOURCEFORGE_MIRROR"
PNP_DATAOPTION=--datarootdir=/usr/local/share/pnp4nagios
PNP_NAME=pnp4nagios

RRDTOOL_URL="http://oss.oetiker.ch/rrdtool/pub/rrdtool-$RRDTOOL_VERSION.tar.gz"


if [ "$(cat /etc/redhat-release 2>/dev/null)" = "Red Hat Enterprise Linux Server release 5.3 (Tikanga)" ]
then
    DISTRO=REDHAT
    DISTRONAME="RedHat 5.3"
    DISTROVERS=5.3
elif [ "$(cat /etc/redhat-release 2>/dev/null)" = "CentOS release 5.5 (Final)" ]
then
    DISTRO=REDHAT
    DISTRONAME="CentOS 5.5"
    DISTROVERS=5.5
elif grep -qi "USE Linux Enterprise Server 11" /etc/SuSE-release 2>/dev/null
then
    DISTRO=SUSE
    DISTRONAME="SLES 11"
    DISTROVERS=11
elif grep -qi "DISTRIB_DESCRIPTION=\"Ubuntu 9.10\"" /etc/lsb-release 2>/dev/null 
then
    DISTRO=UBUNTU
    DISTRONAME="Ubuntu 9.10"
    DISTROVERS=9.10
elif egrep -qi "DISTRIB_DESCRIPTION=\"Ubuntu 10.04(\..*)? LTS\"" /etc/lsb-release 2>/dev/null
then
    DISTRO=UBUNTU
    DISTRONAME="Ubuntu 10.04 LTS"
    DISTROVERS=10.04
else
    debvers=$(cat /etc/debian_version 2>/dev/null)
    debvers=${debvers:0:3}
    if [ "$debvers" = 5.0 ]
    then
        DISTRO=DEBIAN
        DISTRONAME="Debian 5.0 (Lenny)"
        DISTROVERS=5.0
    fi
fi

case "$DISTRO" in 
    REDHAT)
        HTTPD=httpd
        WWWUSER=apache
        WWWGROUP=apache
        activate_initd () { chkconfig $1 on ; }
        add_user_to_group () { gpasswd -a $1 $2 ; }
    ;;
    SUSE)
        HTTPD=apache2
        WWWUSER=wwwrun
        WWWGROUP=www
        activate_initd () { chkconfig $1 on ; }
        add_user_to_group () { groupmod -A $1 $2 ; }
    ;;
    UBUNTU)
        HTTPD=apache2
        WWWUSER=www-data
        WWWGROUP=www-data
        activate_initd () { update-rc.d $1 defaults; }
        add_user_to_group () { gpasswd -a $1 $2 ; }
    ;;
    DEBIAN)
        HTTPD=apache2
        WWWUSER=www-data
        WWWGROUP=www-data
        activate_initd () { update-rc.d $1 defaults; }
        add_user_to_group () { gpasswd -a $1 $2 ; }
    ;;
    *)
	echo "This script does not work on your Linux distribution. Sorry."
	echo "Supported are: Debian 5.0, Ubuntu 9.10, SLES 11 and RedHat/CentOS 5.3"
        exit 1
esac	


# Process command line options
if [ $# -gt 0 ]; then
  while getopts "s:ym" options $OPTS; do
    case $options in
      y)
        YES=1
      ;;
      m)
        WITHOUT_MK=1
        NOTICE="
Setting up without Check_MK!"
      ;;
      s)
        SITE=$OPTARG
      ;;
      *)
        echo "Error: Unknown option."
        exit 1
      ;;
    esac
  done
fi

cat <<EOF

This script is intended for setting up Nagios, PNP4Nagios, NagVis and
Check_MK on a freshly installed Linux system. It will:

 - probably delete your existing Nagios configuration (if any)
 - install missing packages via apt/yum/zypper
 - download software from various internet sources
 - compile Nagios, PNP4Nagios and MK Livestatus
 - install everything into FHS-compliant paths below /etc,
   /var and /usr/local
 - setup Nagios, Apache, PNP4Nagios, NagVis and Check_MK
 - install the check_mk_agent on localhost
 - setup Nagios to monitor localhost

   Your Linux distro:    $DISTRONAME
   Nagios version:       $NAGIOS_VERSION
   Plugins version:      $PLUGINS_VERSION
   Check_MK version:     $CHECK_MK_VERSION
   rrdtool version:      $RRDTOOL_VERSION
   PNP4Nagios version:   $PNP_VERSION
   Nagvis version:       $NAGVIS_VERSION

The output of this script is logged into $LOGFILE.

No user interaction is neccesary.
$NOTICE
EOF

if [ -z "$YES" ]; then
  echo 'Do you want to proceed?'
	echo -n 'Then please enter "yes": '
	read yes
	[ "$yes" = yes ] || exit 0
fi

cat <<EOF

This version of the script supports Multisite-Installations. That
allows you to combine several Nagios instances in one web GUI
using Livestatus and Apache reverse proxy for live data access.
In order to use the feature, you need a unique prefix in the URLs
for each site, e.g. /muc/nagios/ instead of /nagios/, where 'muc'
is the id of the site. Please enter a site id or leave empty
for a classical single-site setup:

EOF

if [ -z "$SITE" ]; then
	echo -n "Site id (leave empty for single site installation): "
	read SITE
fi

if [ -n "$SITE" ] ; then
	SITEURL=/$SITE
	echo -e "\nCool. Doing a multisite installation for site '$SITE'\n"
else
	SITEURL=
fi

set -e


heading ()
{
    echo
    echo '//===========================================================================\\'
    printf "|| %-73s ||\n" "$1"
    echo '\\===========================================================================//'
    echo
}

# Many broken tarballs are out there, which install files as funny users or
# groups and even create directories with permissions 777 (nagios-plugins,
# rrdtool) which unpacking as root
TARXOPTS="--no-same-owner --no-same-permissions"

# -----------------------------------------------------------------------------
heading "Installing missing software"
# -----------------------------------------------------------------------------

if [ "$DISTRO" = DEBIAN -o "$DISTRO" = UBUNTU ]
then
  aptitude -y update
  aptitude -y install psmisc build-essential nail  \
    apache2 libapache2-mod-php5 python php5-gd libgd-dev \
    python-rrdtool xinetd wget libgd2-xpm-dev psmisc less libapache2-mod-python \
    graphviz php5-sqlite sqlite php-gettext locales-all libxml2-dev libpango1.0-dev \
    snmp
    # Hint for Debian: Installing the packages locales-all is normally not neccessary
    # if you use 'dpkg-reconfigure locales' to setup and generate your locales.
    # Correct locales are needed for the localisation of Nagvis.
elif [ "$DISTRO" = SUSE ]
then
   zypper update
   zypper -n install apache2 mailx apache2-mod_python apache2-mod_php5 php5-gd gd-devel \
	xinetd wget xorg-x11-libXpm-devel psmisc less graphviz-devel graphviz-gd \
	php5-sqlite php5-gettext python-rrdtool php5-zlib php5-sockets php5-mbstring gcc \
	cairo-devel libxml-devel libxml2-devel pango-devel gcc-c++ net-snmp php5-iconv
else
   yum update
   yum -y install httpd gcc mailx php php-gd gd-devel xinetd wget psmisc less mod_python \
     sqlite cairo-devel libxml2-devel pango-devel pango libpng-devel freetype freetype-devel libart_lgpl-devel \
     net-snmp
fi

set +e
killall nagios
killall -9 nagios
killall npcd
set -e


if [ -n "$RRDTOOL_VERSION" ] 
then
# -----------------------------------------------------------------------------
    heading "RRDTool"
# -----------------------------------------------------------------------------
    [ -e rrdtool-$RRDTOOL_VERSION ] || wget $RRDTOOL_URL
    rm -rf rrdtool-$RRDTOOL_VERSION
    tar xzf rrdtool-$RRDTOOL_VERSION.tar.gz $TARXOPTS
    pushd rrdtool-$RRDTOOL_VERSION
    ./configure --prefix=/usr/local --localstatedir=/var --enable-perl-site-install
    make -j 16
    make install
    ldconfig

    # Create start script
    cat <<EOF > /etc/init.d/rrdcached
#!/bin/sh

# chkconfig: 345 98 02
# description: RRD Tool cache daemon

### BEGIN INIT INFO
# Provides:       rrdcached
# Required-Start: 
# Required-Stop:  
# Default-Start:  2 3 5
# Default-Stop:
# Description:    Start RRD cache daemon
### END INIT INFO

TIMING="-w 3600 -z 1800 -f 7200"
RRD_DIR="/var/lib/nagios/rrd"
CACHE_DIR="/var/lib/rrdcached"
JOURNAL_DIR="\$CACHE_DIR/journal"
SOCKET="\$CACHE_DIR/rrdcached.sock"
PIDFILE="\$CACHE_DIR/rrdcached.pid"
USER="nagios"
OPTS="\$TIMING -m 0660 -l unix:\$SOCKET -p \$PIDFILE -j \$JOURNAL_DIR -b \$RRD_DIR -B"
DAEMON="/usr/local/bin/rrdcached"

case "\$1" in
    start)
        echo -n 'Starting rrdcached...'
        if [ -e "\$PIDFILE" ] ; then
            PID=\$(cat PIDFILE)
            if [ -n "\$PID" ] && ps \$PID > /dev/null 2>&1 ; then
                echo "still running with pid \$PID! Aborting!"
                exit 1
            fi
            echo "removing stale pid file..."
            rm -f \$PIDFILE
        fi

        # make sure, directories are there (ramdisk!)
        mkdir -p \$CACHE_DIR \$RRD_DIR && 
        chown -R \$USER \$CACHE_DIR \$RRD_DIR &&
        su -s /bin/bash \$USER -c "\$DAEMON \$OPTS" &&
        echo OK || echo Error
    ;;
    stop)
	echo -n 'Stopping rrdcached...'
        PID=\$(cat \$PIDFILE 2>/dev/null)
        if [ -z "\$PID" ] ; then
	    echo "not running."
        elif kill "\$PID" ; then
	    echo "OK"
        else
	    echo "Failed"
        fi
    ;;
    restart)
        \$0 stop
        \$0 start
    ;;
    status)
        echo -n 'Checking status of rrdcached...'
        if [ -e "\$PIDFILE" ] ; then
            PID=\$(cat \$PIDFILE)
            if [ -n "\$PID" ] && ps \$PID > /dev/null 2>&1 ; then
                echo "running"
                exit 0
            fi
        fi
        echo "stopped"
        exit 1
    ;;
    *)
        echo "Usage: \$0 {start|stop|restart|status}"
    ;;
esac
EOF
    chmod 775 /etc/init.d/rrdcached
    activate_initd rrdcached
    popd
fi

# -----------------------------------------------------------------------------
heading "Nagios plugins"
# -----------------------------------------------------------------------------
TAR=nagios-plugins-$PLUGINS_VERSION.tar.gz
[ -e $TAR ] || wget $PLUGINS_URL -O $TAR
rm -rf ${TAR%.tar.gz}
tar xzf $TAR $TARXOPTS
pushd ${TAR%.tar.gz}
./configure \
  --libexecdir=/usr/local/lib/nagios/plugins
make -j 16
make install
popd


# -----------------------------------------------------------------------------
heading "Nagios"
# -----------------------------------------------------------------------------
# Mounting tmpfs to /var/spool/nagios
umount /var/spool/nagios 2>/dev/null || true
mkdir -p /var/spool/nagios
sed -i '\/var\/lib\/nagios\/spool tmpfs/d' /etc/fstab
echo 'tmpfs /var/spool/nagios tmpfs defaults 0 0' >> /etc/fstab
mount /var/spool/nagios

TAR=nagios-$NAGIOS_VERSION.tar.gz
[ -e $TAR ] || wget $NAGIOS_URL -O $TAR
rm -rf ${TAR%.tar.gz}
tar xzf $TAR $TARXOPTS
pushd ${TAR%.tar.gz}
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
  --with-cgiurl=$SITEURL/nagios/cgi-bin \
  --with-htmurl=$SITEURL/nagios \
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

make \
  install \
  install-cgis \
  install-html \
  install-init \
  install-commandmode \
  install-config 

chown -R root.root \
  /usr/local/bin/nagios* \
  /usr/local/*/nagios \
  /etc/nagios

sed -i '/CONFIG ERROR/a\                        $NagiosBin -v $NagiosCfgFile'  /etc/init.d/nagios


mkdir -p /var/spool/nagios/tmp
chown -R nagios.nagios /var/lib/nagios
mkdir -p /var/log/nagios/archives
chown -R nagios.nagios /var/log/nagios
mkdir -p /var/cache/nagios
chown nagios.nagios /var/cache/nagios
mkdir -p /var/run/nagios/rw
chown nagios.nagios /var/run/nagios/rw
chmod 2755 /var/run/nagios/rw
mkdir -p  /var/lib/nagios/rrd
chown nagios.nagios /var/lib/nagios/rrd
mkdir -p /var/spool/nagios/pnp/npcd
chown -R nagios.nagios /var/spool/nagios
chown root.nagios /usr/local/lib/nagios/plugins/check_icmp
chmod 4750 /usr/local/lib/nagios/plugins/check_icmp
chown nagios.nagios /var/log/nagios

# Fix F5 problem in Nagios webinterface
sed -i '1s/.*$/<?php header("Cache-Control: max-age=7200, public"); ?>\n&/g' /usr/local/share/nagios/htdocs/index.php

# Prepare configuration
popd
pushd /etc/nagios
mv nagios.cfg nagios.cfg-example
mv objects conf.d-example
: > resource.cfg
cat <<EOF > nagios.cfg
# Paths
lock_file=/var/run/nagios.lock
temp_file=/var/spool/nagios/nagios.tmp
temp_path=/var/spool/nagios/tmp
log_archive_path=/var/log/nagios/archives
check_result_path=/var/spool/nagios/checkresults
state_retention_file=/var/lib/nagios/retention.dat
debug_file=/var/log/nagios/nagios.debug
command_file=/var/run/nagios/rw/nagios.cmd
log_file=/var/log/nagios/nagios.log
cfg_dir=/etc/nagios/conf.d
object_cache_file=/var/cache/nagios/objects.cache
precached_object_file=/var/cache/nagios/objects.precache
resource_file=/etc/nagios/resource.cfg
status_file=/var/spool/nagios/status.dat

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

status_update_interval=30
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
date_format=iso8601
enable_embedded_perl=0
use_regexp_matching=0
use_true_regexp_matching=0
use_large_installation_tweaks=1
enable_environment_macros=0
debug_level=0
debug_verbosity=0
max_debug_file_size=1000000

# PNP4Nagios
process_performance_data=1
service_perfdata_file=/var/spool/nagios/pnp/service-perfdata
service_perfdata_file_template=DATATYPE::SERVICEPERFDATA\tTIMET::\$TIMET\$\tHOSTNAME::\$HOSTNAME\$\tSERVICEDESC::\$SERVICEDESC\$\tSERVICEPERFDATA::\$SERVICEPERFDATA\$\tSERVICECHECKCOMMAND::\$SERVICECHECKCOMMAND\$\tHOSTSTATE::\$HOSTSTATE\$\tHOSTSTATETYPE::\$HOSTSTATETYPE\$\tSERVICESTATE::\$SERVICESTATE\$\tSERVICESTATETYPE::\$SERVICESTATETYPE\$
service_perfdata_file_mode=a
service_perfdata_file_processing_interval=10
service_perfdata_file_processing_command=process-service-perfdata-file

host_perfdata_file=/var/spool/nagios/pnp/host-perfdata
host_perfdata_file_template=DATATYPE::HOSTPERFDATA\tTIMET::\$TIMET\$\tHOSTNAME::\$HOSTNAME\$\tHOSTPERFDATA::\$HOSTPERFDATA\$\tHOSTCHECKCOMMAND::\$HOSTCHECKCOMMAND\$\tHOSTSTATE::\$HOSTSTATE\$\tHOSTSTATETYPE::\$HOSTSTATETYPE\$
host_perfdata_file_mode=a
host_perfdata_file_processing_interval=10
host_perfdata_file_processing_command=process-host-perfdata-file

# Illegal characters
EOF

grep 'illegal.*=' nagios.cfg-example >> nagios.cfg

# Modify init-script: It must create the temp directory,
# as it is in a tmpfs. And on Ubuntu /var/run is also a ramdisk,
# so create /var/run/nagios/rw also in startskript.
sed -i -e '/^[[:space:]]start)/a                mkdir -p /var/spool/nagios/tmp /var/spool/nagios/checkresults /var/run/nagios/rw' \
       -e '/^[[:space:]]start)/a                chown nagios.nagios /var/spool/nagios/tmp /var/spool/nagios/checkresults /var/run/nagios/rw' \
       -e '/^[[:space:]]start)/a                chmod 2755 /var/run/nagios/rw' /etc/init.d/nagios

# Make CGIs display addons in right frame, not in a new window
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
       command_name    process-service-perfdata-file
       command_line    /bin/mv /var/spool/nagios/pnp/service-perfdata /var/spool/nagios/pnp/npcd/service-perfdata.\$TIMET\$
}

define command {
       command_name    process-host-perfdata-file
       command_line    /bin/mv /var/spool/nagios/pnp/host-perfdata /var/spool/nagios/pnp/npcd/host-perfdata.\$TIMET\$
}
EOF


# Password is 'test'
echo 'nagiosadmin:vWQwFr7mwjvmI' > htpasswd


mkdir -p /etc/$HTTPD/conf.d
ln -sfn /etc/nagios/$HTTPD.conf /etc/$HTTPD/conf.d/nagios.conf

rm -rf conf.d-example

popd

# =============================================================================
# PNP4Nagios
# =============================================================================

# Compile and install PNP4Nagios
heading "PNP4Nagios"
TAR=$PNP_NAME-$PNP_VERSION.tar.gz
[ -e $TAR ] || wget "$PNP_URL" -O $TAR
rm -rf ${TAR%.tar.gz}
tar xzf $TAR $TARXOPTS
pushd ${TAR%.tar.gz} 

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
make install install-config install-webconf
install -m 644 contrib/ssi/status-header.ssi /usr/local/share/nagios/htdocs/ssi/
if [ "$SITE" ] ; then
    sed -i "s@/pnp4nagios@$SITEURL/pnp4nagios@" /usr/local/share/nagios/htdocs/ssi/status-header.ssi 
fi

rm -rf /etc/nagios/check_commands
popd
pushd /etc/nagios
mv rra.cfg-sample rra.cfg
rm -f npcd.cfg*
cat <<EOF > npcd.cfg
user = nagios
group = nagios
log_type = file
log_file = /var/log/nagios/npcd.log
max_logfile_size = 10485760
log_level = 0
perfdata_spool_dir = /var/spool/nagios/pnp/npcd
perfdata_file_run_cmd = /usr/local/lib/nagios/process_perfdata.pl
perfdata_file_run_cmd_args = -b
identify_npcd = 1
npcd_max_threads = 5
sleep_time = 15
load_threshold = 0.0
pid_file = /var/run/npcd.pid
# This line must be here. Bug in ncpd. Sorry.
EOF

rm -f process_perfdata.cfg*
cat <<EOF > process_perfdata.cfg
TIMEOUT = 5
USE_RRDs = 1 
RRDPATH = /var/lib/nagios/rrd
RRDTOOL = /usr/local/bin/rrdtool
CFG_DIR = /etc/nagios
RRD_STORAGE_TYPE = SINGLE
RRD_HEARTBEAT = 8460 
RRA_CFG = /etc/nagios/rra.cfg
RRA_STEP = 60
LOG_FILE = /var/log/nagios/perfdata.log
LOG_LEVEL = 0
XML_ENC = UTF-8
XML_UPDATE_DELAY = 3600
RRD_DAEMON_OPTS = unix:/var/lib/rrdcached/rrdcached.sock
EOF

rm -f config.php*
cat <<EOF > config.php
<?php
\$conf['use_url_rewriting'] = 1;
\$conf['rrdtool'] = "/usr/local/bin/rrdtool";
\$conf['graph_width'] = "500";
\$conf['graph_height'] = "100";
\$conf['pdf_width'] = "675";
\$conf['pdf_height'] = "100";
\$conf['graph_opt'] = ""; 
\$conf['pdf_graph_opt'] = ""; 
\$conf['rrdbase'] = "/var/lib/nagios/rrd/";
\$conf['page_dir'] = "/etc/nagios/pages/";
\$conf['special_template_dir'] = '/usr/local/share/pnp4nagios/templates.special';
\$conf['refresh'] = "90";
\$conf['max_age'] = 60*60*6;   
\$conf['temp'] = "/var/tmp";
\$conf['pnp_base'] = "$SITEURL/pnp4nagios";
\$conf['base_url'] = "$SITEURL/pnp4nagios";
\$conf['nagios_base'] = "$SITEURL/nagios/cgi-bin";
\$conf['allowed_for_service_links'] = "EVERYONE";
\$conf['allowed_for_host_search'] = "EVERYONE";
\$conf['allowed_for_host_overview'] = "EVERYONE";
\$conf['allowed_for_pages'] = "EVERYONE";
\$conf['overview-range'] = 1 ;
\$conf['popup-width'] = "300px";
\$conf['ui-theme'] = 'multisite';
\$conf['lang'] = "en_US";
\$conf['date_fmt'] = "d.m.y G:i";
\$conf['enable_recursive_template_search'] = 0;
\$conf['show_xml_icon'] = 1;
\$conf['use_fpdf'] = 1;	
\$conf['background_pdf'] = '/etc/nagios/background.pdf' ;
\$conf['use_calendar'] = 1;
\$views[0]["title"] = "4 Hours";
\$views[0]["start"] = ( 60*60*4 );
\$views[1]["title"] = "24 Hours";
\$views[1]["start"] = ( 60*60*24 );
\$views[2]["title"] = "One Week";
\$views[2]["start"] = ( 60*60*24*7 );
\$views[3]["title"] = "One Month";
\$views[3]["start"] = ( 60*60*24*30 );
\$views[4]["title"] = "One Year";
\$views[4]["start"] = ( 60*60*24*365 );
\$conf['RRD_DAEMON_OPTS'] = 'unix:/var/lib/rrdcached/rrdcached.sock';
\$conf['template_dir'] = '/usr/local/share/pnp4nagios';
\$conf['multisite_base_url'] = "$SITEURL/check_mk";
\$conf['multisite_site'] = "$SITE";
?>
EOF

cat <<EOF > /etc/$HTTPD/conf.d/pnp4nagios.conf
Alias $SITEURL/pnp4nagios "/usr/local/share/pnp4nagios"

<Directory "/usr/local/share/pnp4nagios">
   	AllowOverride None
   	Order allow,deny
   	Allow from all
   	#
   	# Use the same value as defined in nagios.conf
   	#
   	AuthName "Nagios Access"
   	AuthType Basic
   	AuthUserFile /etc/nagios/htpasswd
   	Require valid-user
	<IfModule mod_rewrite.c>
		# Turn on URL rewriting
		RewriteEngine On
		Options FollowSymLinks
		# Installation directory
		RewriteBase $SITEURL/pnp4nagios/
		# Protect application and system files from being viewed
		RewriteRule ^(application|modules|system) - [F,L]
		# Allow any files or directories that exist to be displayed directly
		RewriteCond %{REQUEST_FILENAME} !-f
		RewriteCond %{REQUEST_FILENAME} !-d
		# Rewrite all other URLs to index.php/URL
		RewriteRule .* index.php/\$0 [PT,L]
	</IfModule>
</Directory>
EOF

chown -R root.root pages *.pdf pnp4nagios_release *.cfg
popd


mkdir -p /etc/init.d
cat <<EOF > /etc/init.d/npcd
#!/bin/sh

# chkconfig: 345 98 02
# description: PNP4Nagios NCPD

### BEGIN INIT INFO
# Provides:       npcd
# Required-Start: $networking
# Required-Stop:  $networking
# Default-Start:  2 3 5
# Default-Stop:
# Description:    Start NPCD of PNP4Nagios
### END INIT INFO

case "\$1" in
    start)
	# make sure, directories are there (ramdisk!)
	mkdir -p /var/spool/nagios/pnp/npcd
	chown -R nagios.nagios /var/spool/nagios
 	echo -n 'Starting NPCD...'
	/usr/local/bin/npcd -d -f /etc/nagios/npcd.cfg && echo OK || echo Error
        ;;
    stop)
	echo -n 'Stopping NPCD...'
	killall npcd && echo OK || echo Error
    ;;
    restart)
	\$0 stop
	\$0 start
    ;;
    *)
	echo "Usage: \0 {start|stop|restart}"
    ;;
esac
EOF
chmod 755 /etc/init.d/npcd

activate_initd npcd
/etc/init.d/npcd start

echo "Enabling mod_rewrite"
a2enmod rewrite || true

rm -f /usr/local/share/pnp4nagios/install.php

# Fixes for Multisite
if [ "$SITE" ]
then
    sed -i 's#^.config..site_domain...*#\$config["site_domain"] = "'"$SITEURL"'/pnp4nagios";#' /usr/local/share/pnp4nagios/application/config/config.php
cat  <<EOF > /usr/local/share/pnp4nagios/application/views/popup.php
<table><tr><td>
<?php
foreach ( \$this->data->STRUCT as \$KEY=>\$VAL){
	\$source = \$VAL['SOURCE'];
	echo "<tr><td>\n";
	echo "<img width=\"".\$imgwidth."\" src=\"$SITEURL/pnp4nagios/image?host=\$host&srv=\$srv&view=\$view&source=\$source\">\n";
	echo "</td></tr>\n";
}
?>
</table>
EOF
fi



# -----------------------------------------------------------------------------
# Und auch noch Nagvis
# -----------------------------------------------------------------------------
if [ "$NAGVIS_VERSION" ]
then
	heading "NagVis"
	TAR=nagvis-$NAGVIS_VERSION.tar.gz
	[ -e $TAR ] || wget "$NAGVIS_URL" -O $TAR
	rm -rf ${TAR%.tar.gz}
	tar xzf $TAR $TARXOPTS
	pushd ${TAR%.tar.gz}
	rm -rf /usr/local/share/nagvis
	./install.sh -q -F -c y \
	  -u $WWWUSER \
	  -g $WWWGROUP \
	  -w /etc/$HTTPD/conf.d \
	  -W $SITEURL/nagvis \
	  -B /usr/local/bin/nagios \
	  -b /usr/bin \
	  -p /usr/local/share/nagvis \
	  -B /usr/local/bin
	popd

	cat <<EOF > /usr/local/share/nagvis/etc/nagvis.ini.php
[paths]
base="/usr/local/share/nagvis/"
htmlbase="$SITEURL/nagvis/"
htmlcgi="$SITEURL/nagios/cgi-bin"

[defaults]
backend="live_1"

[backend_live_1]
backendtype="mklivestatus"
socket="unix:/var/run/nagios/rw/live"
htmlcgi="$SITEURL/nagios/cgi-bin"
EOF
    cat <<EOF > /etc/$HTTPD/conf.d/nagvis.conf
Alias $SITEURL/nagvis/ /usr/local/share/nagvis/share/
<Directory /usr/local/share/nagvis/share/>
   allow from all
   AuthName "Nagios Access"
   AuthType Basic
   AuthUserFile "/etc/nagios/htpasswd"
   require valid-user 
</Directory>
EOF
fi


# -----------------------------------------------------------------------------
# Apache
# -----------------------------------------------------------------------------
cat <<EOF > /etc/$HTTPD/conf.d/nagios.conf
RedirectMatch ^/$ $SITEURL/nagios/

ScriptAlias $SITEURL/nagios/cgi-bin/ /usr/local/lib/nagios/cgi-bin/
<Directory /usr/local/lib/nagios/cgi-bin/>
   allow from all
   AuthName "Nagios Access"
   AuthType Basic
   AuthUserFile "/etc/nagios/htpasswd"
   require valid-user 
</Directory>

Alias $SITEURL/nagios/ /usr/local/share/nagios/htdocs/
<Directory /usr/local/share/nagios/htdocs/>
   allow from all
   AuthName "Nagios Access"
   AuthType Basic
   AuthUserFile "/etc/nagios/htpasswd"
   require valid-user 
</Directory>
EOF

if [ "$SITE" ] ; then
cat <<EOF > /etc/$HTTPD/conf.d/multisite.conf
# Transparent access to web based addons and the classical Nagios GUI
# via mod_rewrite, mod_proxy and mod_proxy_http (make sure, those are enabled)!

# For each remote site, define a Location like the following.
# In this example, /nag02 is the site prefix and 192.168.56.7
# the IP address of the remote web server

<Location /nag02>
    RewriteEngine On
    RewriteRule ^/.+/nag02/(.*) http://192.168.56.7/nag02/\$1 [P]
</Location>

# Need some debugging => turn on a logfile here:
# RewriteLog /tmp/rewrite.log
# RewriteLogLevel 3
EOF
    a2enmod proxy || true
    a2enmod proxy_http || true
fi


add_user_to_group $WWWUSER nagios
/etc/init.d/$HTTPD stop
/etc/init.d/$HTTPD start
killall nagios || true
/etc/init.d/nagios start
activate_initd nagios || true

if [ "$CHECK_MK_VERSION" -a -z "$WITHOUT_MK" ]
then
    # -----------------------------------------------------------------------------
    heading "Check_MK"
    # -----------------------------------------------------------------------------
    if [ ! -e check_mk-$CHECK_MK_VERSION.tar.gz ]
    then
	wget "$CHECK_MK_URL"
    fi
    rm -rf check_mk-$CHECK_MK_VERSION
    tar xzf check_mk-$CHECK_MK_VERSION.tar.gz $TARXOPTS
    pushd check_mk-$CHECK_MK_VERSION
    rm -f ~/.check_mk_setup.conf
    rm -rf /var/lib/check_mk /etc/check_mk
    rm -f /etc/$HTTPD/conf.d/zzz_check_mk.conf

    # Set some non-default paths which cannot be 
    # autodetected
    cat <<EOF > ~/.check_mk_setup.conf 
check_icmp_path='/usr/local/lib/nagios/plugins/check_icmp'
rrddir='/var/lib/nagios/rrd'
EOF

    if [ "$SITE" ]; then
	echo "url_prefix='$SITEURL/'" >> ~/.check_mk_setup.conf
    fi

    ./setup.sh --yes

    echo 'do_rrd_update = False' >> /etc/check_mk/main.mk
    echo "nagvis_base_url = '$SITEURL/nagvis'" >> /etc/check_mk/multisite.mk
    popd

    echo "Enabling mod_python"
    a2enmod python || true

    # Apache neu starten
    echo "Restarting apache"
    /etc/init.d/$HTTPD restart
    activate_initd $HTTPD

    # side.html anpassen
    HTML='<div class="navsectiontitle">Check_MK</div><div class="navsectionlinks"><ul class="navsectionlinks"><li><a href="'"$SITEURL"'/check_mk/" target="_blank">Multisite</a></li></ul></div></div><div class="navsection"><div class="navsectiontitle">NagVis</div><div class="navsectionlinks"><ul class="navsectionlinks"><li><a href="'"$SITEURL"'/nagvis/" target="<?php echo $link_target;?>">Overview page</a></li></div></div><div class="navsection">'
    QUOTE=${HTML//\//\\/}
    sed -i "/.*Reports<.*$/i$QUOTE" /usr/local/share/nagios/htdocs/side.php

    # -----------------------------------------------------------------------------
    # Agent fuer localhost
    # -----------------------------------------------------------------------------
    mkdir -p /etc/xinetd.d
    cp /usr/share/check_mk/agents/xinetd.conf /etc/xinetd.d/check_mk
    mkdir -p /usr/bin
    install -m 755 /usr/share/check_mk/agents/check_mk_agent.linux /usr/bin/check_mk_agent
    /etc/init.d/xinetd stop || true
    /etc/init.d/xinetd start
    activate_initd xinetd

    cat <<EOF > /etc/check_mk/main.mk
all_hosts = [ 'localhost' ]
do_rrd_update = False
EOF
    check_mk -I alltcp
    rm /etc/nagios/conf.d/localhost.cfg
    check_mk -R

    # -----------------------------------------------------------------------------
    # Livestatus xinetd
    # -----------------------------------------------------------------------------

    cat <<EOF > /etc/xinetd.d/livestatus
service livestatus
{
	type		= UNLISTED
	port		= 6557
	socket_type	= stream
	protocol	= tcp
	wait		= no
# limit to 100 connections per second. Disable 3 secs if above.
	cps             = 100 3
# Disable TCP delay, makes connection more responsive
	flags           = NODELAY
	user		= nagios
	server		= /usr/bin/unixcat
	server_args     = /var/run/nagios/rw/live
# configure the IP address(es) of your Nagios server here:
#	only_from       = 127.0.0.1 10.0.20.1 10.0.20.2
	disable		= no
}
EOF
    /etc/init.d/xinetd restart
fi

heading "Starting rrdcached"
/etc/init.d/rrdcached start

heading "Cleaning up"
rm -f /etc/nagios/*.cfg-*

cat <<EOF

Nagios and the addons have been installed into the following paths:

 /etc/nagios              configuration of Nagios & PNP4Nagios
 /etc/check_mk            configuration of check_mk
 /etc/init.d/nagios       start script for Nagios

 /var/lib/nagios          data directory of Nagios
 /var/spool/nagios        spool files for Nagios (in Ramdisk)
 /var/log/nagios          log files of Nagios
 /var/lib/check_mk        data directory of Check_MK

 /usr/local               programs, scripts, fixed data

Now you can point your browser to to http://${HOSTNAME:-localhost}$SITEURL/nagios/
and login with 'nagiosadmin' and 'test'.  You can change the password with
# htpasswd /etc/nagios/htpasswd nagiosadmin

The new Check_MK Multisite GUI is awaiting you here:
http://${HOSTNAME:-localhost}$SITEURL/check_mk/

EOF

if [ "$SITE" ] ; then
cat <<EOF
Multisite TODO: You need to alter the apache configuration to make 
the Multisite setup work.

A sample configuration is placed here: /etc/$HTTPD/conf.d/multisite.conf

You need to add the single sites to the master server or all sites
to their partners.

EOF
fi
