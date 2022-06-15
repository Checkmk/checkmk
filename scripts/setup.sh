#!/bin/bash
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
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.


VERSION=1.6.0p30
NAME=check_mk
LANG=
LC_ALL=
SETUPCONF=~/.check_mk_setup.conf

# Find path to ourselves
SRCDIR=${0%/*}
if [ "$SRCDIR" = "$0" ] ; then SRCDIR=. ; fi
if [ ! -e "$SRCDIR/setup.sh" ] ; then
    echo "Cannot find location of setup.sh.">&2
    echo "Please call setup.sh with its complete path." >&2
    exit 1
fi

# If called with "--yes" we assume yes to all questions
# and do not display anything other then error messages
if [ "$1" = "--yes" ]
then
    YES=yes
else
    YES=
fi


# Install check_mk into user defined locations
# This script is run during packaging for RPM
# and DEB. You can also run it manually for a
# customized setup

if [ $UID = 0 -o -n "$DESTDIR" ] ; then
    ROOT=yes
    if [ "$DESTDIR" = / ] ; then
	DESTDIR=
    fi
else
    ROOT=
    DESTDIR=
fi

SUMMARY=
DIRINFO="# Written by setup of check_mk $VERSION at $(date)"

dir_already_configured ()
{
    # if DESTDIR is used, setup config is never used.
    if [ -n "$DESTDIR" ] ; then return 1 ; fi

    # Check if this path has already been configured in a previous setup
    grep -q "^$1=" $SETUPCONF >/dev/null 2>&1
}


ask_dir ()
{
    if [ $1 != -d ] ; then
	prefix="$(pwd)/"
    else
	prefix=""
	shift
    fi
    VARNAME=$1
    DEF_ROOT=$2
    DEF_USER=$3
    DEF_OMD=$4
    SHORT=$5
    DESCR=$6

    # maybe variable already set (via environment, via autodetection,
    # or view $SETUPCONF)
    eval "DIR="'$'"$VARNAME"

    # if DESTDIR is set, the user is never asked, but the
    # variable must be set via the environment. Otherwise
    # the default value is used.
    if [ -n "$DESTDIR" ] ; then
	if [ -z "$DIR" ] ; then
	    DIR=$DEF_ROOT
	fi
        eval "$VARNAME='$DIR'"
    else
        # Three cases for each variable:
        # 1) variable is set in ~/.check_mk_setup.conf
        # 2) variable is autodetected
        # 3) variable is unset

	if [ -z "$DIR" ] ; then
	    class="[1;44;37m default [0m"
            if [ "$OMD_SITE" ] ; then
                DEF=$DEF_OMD
	    elif [ "$ROOT" ] ; then
		DEF=$DEF_ROOT
	    else
		DEF=$DEF_USER
	    fi
	elif dir_already_configured "$VARNAME" ; then
	    DEF=$DIR
	    class="[1;43;37m previous [0m"
	else
	    class="[1;42;37m autodetected [0m"
	    DEF=$DIR
	fi
	PRINTOUT="$class --> [1;44;36m"
	if [ -z "$YES" ] ; then
	    read -p "[1;4m$SHORT[0m
$DESCR:
($PRINTOUT$DEF[0m): " DIR
	    if [ -z "$DIR" ] ; then DIR=$DEF ; fi
        else
	    DIR=$DEF
        fi

	# Handle relative paths
        if [ "${DIR:0:1}" != / ] ; then
	    DIR="$prefix$DIR"
        fi
        eval "$VARNAME='$DIR'"
    fi

    SUMMARY="$SUMMARY
$(printf "[44;37m %-30s [1;45;37m %-39s [0m" "$SHORT" "$DIR")"

    DIRINFO="$DIRINFO
$VARNAME='$DIR'"
    if [ -z "$YES" ] ; then echo ; fi
}

TITLENO=0
ask_title ()
{
    if [ "$YES" ] ; then return ; fi
    TITLENO=$((TITLENO + 1))
    f="[44;37;1m  %-69s  [0m\n"
    echo
    printf "$f" ""
    printf "$f" "$TITLENO) $*"
    printf "$f" ""
    echo
}

if [ -z "$YES" ] ; then
    cat <<EOF
[H[2J
[1;44;37m               ____ _               _        __  __ _  __               [0m
[1;44;37m              / ___| |__   ___  ___| | __   |  \/  | |/ /               [0m
[1;44;37m             | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /                [0m
[1;44;37m             | |___| | | |  __/ (__|   <    | |  | | . \                [0m
[1;44;37m              \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\               [0m
[1;44;37m                                       |_____|                          [0m
[1;44;37m                                                                        [0m
[1;45;37m   Check_MK manual setup           $(printf "%32s" Version:' '$VERSION)     [0m
[1;41;33m                                                                        [0m
[1;41;37m  The manual setup of Check_MK via ./setup.sh is not possible           [0m
[1;41;37m  anymore. Check_MK is only supported to be used with the               [0m
[1;41;37m  Check_MK Raw or Enterprise Edition packages.                          [0m
[1;41;37m                                                                        [0m
[1;41;37m  These have many advantages:                                           [0m
[1;41;37m                                                                        [0m
[1;41;37m   - Very easy installation via a single RPM/DEB package                [0m
[1;41;37m   - Contains fully integrated complete monitoring environment          [0m
[1;41;37m   - Does not need installation of Nagios, PNP4Nagios or plugins        [0m
[1;41;37m   - Supports multiple versions of Check_MK at the same time            [0m
[1;41;37m   - Supports multiple monitoring instances on one server               [0m
[1;41;37m   - Actively maintainained by the Check_MK project                     [0m
[1;41;37m                                                                        [0m
[1;44;37m                                                                        [0m
[1;44;37m  You can download the Check_MK Raw Edition for free here:              [0m
[1;44;33m                                                                        [0m
[1;44;36m  http://mathias-kettner.com/download                                   [0m
[1;44;37m                                                                        [0m
[1;44;37m  Installation instructions are here:                                   [0m
[1;44;37m                                                                        [0m
[1;44;36m  http://mathias-kettner.com/cms_introduction_packages.html             [0m
[1;44;37m                                                                        [0m

EOF
    exit 1
fi

if [ -z "$DESTDIR" ]
then
    if [ -n "$YES" ] ; then
	if OUTPUT=$(python $SRCDIR/autodetect.py 2>/dev/null) ; then
	    eval "$OUTPUT"
	fi
    elif OUTPUT=$(python $SRCDIR/autodetect.py)
    then
        eval "$OUTPUT"
	if [ -z "$YES" ] ; then
	    printf "[1;37;42m %-71s [0m\n" "* Found running Nagios process, autodetected $(echo "$OUTPUT" | grep -v '^\(#\|$\)' | wc -l) settings."
	fi
    fi
fi

if [ -z "$DESTDIR" -a -e "$SETUPCONF" ] && . $SETUPCONF
then
    if [ -z "$YES" ] ; then
        printf "[1;37;43m %-71s [0m\n" "* Read $(grep = $SETUPCONF | wc -l) settings from previous setup from $SETUPCONF."
    fi
fi


HOMEBASEDIR=$HOME/$NAME

ask_title "Installation directories of check_mk"


ask_dir bindir /usr/bin $HOMEBASEDIR/bin $OMD_ROOT/local/bin "Executable programs" \
  "Directory where to install executable programs such as check_mk itself.
This directory should be in your search path (\$PATH). Otherwise you
always have to specify the installation path when calling check_mk"

ask_dir confdir /etc/$NAME $HOMEBASEDIR $OMD_ROOT/etc/check_mk "Check_MK configuration" \
  "Directory where check_mk looks for its main configuration file main.mk.
An example configuration file will be installed there if no main.mk is
present from a previous version"

ask_dir sharedir /usr/share/$NAME $HOMEBASEDIR $OMD_ROOT/local/share/check_mk "Check_MK software" \
  "The base directory for the software installation of Check_MK. This
directory will get the subdirectories checks, modules, web, locale and
agents. Note: in previous versions it was possible to specify each of
those directories separately. This is no longer possible"

ask_dir docdir /usr/share/doc/$NAME $HOMEBASEDIR/doc $OMD_ROOT/local/share/check_mk/doc "documentation" \
  "Some documentation about check_mk will be installed here. Please note,
however, that most of check_mk's documentation is available only online at
http://mathias-kettner.de/check_mk.html"

ask_dir checkmandir /usr/share/doc/$NAME/checks $HOMEBASEDIR/doc/checks $OMD_ROOT/local/share/check_mk/checkman "check manuals" \
  "Directory for manuals for the various checks. The manuals can be viewed
with check_mk -M <CHECKNAME>"

ask_dir vardir /var/lib/$NAME $HOMEBASEDIR/var $OMD_ROOT/var/check_mk "working directory of Check_MK" \
  "Check_MK will create log files, automatically created checks and
other files into this directory. The setup will create several subdirectories
and makes them writable by the Nagios process"

PYTHON_PATH=$(python -c "import sys; print([ p for p in sys.path if p.startswith(\"/usr/lib/\") and p.count(\"/\") == 3 ][0])" 2>/dev/null)
if [ -z "$PYTHON_PATH" ]; then
    PYTHON_PATH=/usr/lib/python2.7
fi

ask_dir python_lib_dir $PYTHON_PATH $HOMEBASEDIR/python $OMD_ROOT/lib/python "Check_MK python modules" \
  "Check_MKs different components share common code in Python modules. These
have to be installed in a directory where the used Python interpreter is
searching for modules."

ask_title "Configuration of Linux/UNIX Agents"


ask_dir agentslibdir /usr/lib/check_mk_agent $HOMEBASEDIR/check_mk_agent /usr/lib/check_mk_agent "extensions for agents" \
  "This directory will not be created on the server. It will be hardcoded
into the Linux and UNIX agents. The agent will look for extensions in the
subdirectories plugins/ and local/ of that directory"

ask_dir agentsconfdir /etc/check_mk $HOMEBASEDIR /etc/check_mk "configuration dir for agents" \
  "This directory will not be created on the server. It will be hardcoded
into the Linux and UNIX agents. The agent will look for its configuration
files here (currently only the logwatch extension needs a configuration file)"

ask_title "Integration with Nagios"

ask_dir -d nagiosuser nagios $(id -un) "$OMD_SITE" "Name of Nagios user" \
  "The working directory for check_mk contains several subdirectories
that need to be writable by the Nagios user (which is running check_mk
in check mode). Please specify the user that should own those
directories"

ask_dir -d wwwuser www-data www-data "$OMD_SITE" "User of Apache process" \
  "Check_MK WATO (Web Administration Tool) needs a sudo configuration,
such that Apache can run certain commands as $(id -un). If you specify
the correct user of the apache process here, then we can create a valid
sudo configuration for you later:"

ask_dir -d wwwgroup nagios $(id -un) "$OMD_SITE" "Common group of Nagios+Apache" \
  "Check_mk creates files and directories while running as $nagiosuser.
Some of those need to be writable by the user that is running the webserver.
Therefore a group is needed in which both Nagios and the webserver are
members (every valid Nagios installation uses such a group to allow
the web server access to Nagios' command pipe):"

ask_dir nagios_binary /usr/sbin/nagios $HOMEBASEDIR/nagios/bin/nagios $OMD_ROOT/bin/nagios "Nagios binary" \
  "The complete path to the Nagios executable. This is needed by the
option -R/--restart in order to do a configuration check."

ask_dir nagios_config_file /etc/nagios/nagios.cfg $HOMEBASEDIR/nagios/etc/nagios.cfg $OMD_ROOT/tmp/nagios/nagios.cfg "Nagios main configuration file" \
  "Path to the main configuration file of Nagios. That file is always
named 'nagios.cfg'. The default path when compiling Nagios yourself
is /usr/local/nagios/etc/nagios.cfg. The path to this file is needed
for the check_mk option -R/--restart"

ask_dir nagconfdir /etc/nagios/objects $HOMEBASEDIR/nagios/etc $OMD_ROOT/etc/nagios/conf.d "Nagios object directory" \
  "Nagios' object definitions for hosts, services and contacts are
usually stored in various files with the extension .cfg. These files
are located in a directory that is configured in nagios.cfg with the
directive 'cfg_dir'. Please specify the path to that directory
(If the autodetection can find your configuration
file but does not find at least one cfg_dir directive, then it will
add one to your configuration file for your conveniance)"

ask_dir nagios_startscript /etc/init.d/nagios /etc/init.d/nagios $OMD_ROOT/etc/init.d/nagios "Nagios startskript" \
  "The complete path to the Nagios startskript is used by the option
-R/--restart to restart Nagios."

ask_dir nagpipe /var/log/nagios/rw/nagios.cmd $HOMEBASEDIR/var/nagios/rw/nagios.cmd $OMD_ROOT/tmp/run/nagios.cmd "Nagios command pipe" \
  "Complete path to the Nagios command pipe. check_mk needs write access
to this pipe in order to operate"

ask_dir check_result_path /usr/local/nagios/var/spool/checkresults $HOMEBASEDIR/var/nagios/checkresults $OMD_ROOT/tmp/nagios/checkresults "Check results directory" \
  "Complete path to the directory where Nagios stores its check results.
Using that directory instead of the command pipe is faster."

ask_dir nagios_status_file /var/log/nagios/status.dat /var/log/nagios/status.dat $OMD_ROOT/tmp/nagios/status.dat "Nagios status file" \
  "The web pages of check_mk need to read the file 'status.dat', which is
regularily created by Nagios. The path to that status file is usually
configured in nagios.cfg with the parameter 'status_file'. If
that parameter is missing, a compiled-in default value is used. On
FHS-conforming installations, that file usually is in /var/lib/nagios
or /var/log/nagios. If you've compiled Nagios yourself, that file
might be found below /usr/local/nagios"

ask_dir check_icmp_path /usr/lib/nagios/plugins/check_icmp $HOMEBASEDIR/libexec/check_icmp $OMD_ROOT/lib/nagios/plugins/check_icmp "Path to check_icmp" \
  "check_mk ships a Nagios configuration file with several host and
service templates. Some host templates need check_icmp as host check.
That check plugin is contained in the standard Nagios plugins.
Please specify the complete path (dir + filename) of check_icmp"

# -------------------------------------------------------------------
ask_title "Integration with Apache"
# -------------------------------------------------------------------

ask_dir -d url_prefix / / /$OMD_SITE/ "URL Prefix for Web addons" \
 "Usually the Multisite GUI is available at /check_mk/ and PNP4Nagios
is located at /pnp4nagios/. In some cases you might want to define some
prefix in order to be able to run more instances of Nagios on one host.
If you say /test/ here, for example, then Multisite will be located
at /test/check_mk/. Please do not forget the trailing slash."

ask_dir apache_config_dir /etc/apache2/conf.d /etc/apache2/conf.d $OMD_ROOT/etc/apache/conf.d "Apache config dir" \
 "Check_mk ships several web pages implemented in Python with Apache
mod_python. That module needs an apache configuration section which
will be installed by this setup. Please specify the path to a directory
where Apache reads in configuration files."

ask_dir htpasswd_file /etc/nagios/htpasswd.users $HOMEBASEDIR/etc/htpasswd.users $OMD_ROOT/etc/htpasswd "HTTP authentication file" \
 "Check_mk's web pages should be secured from unauthorized access via
HTTP authenticaion - just as Nagios. The configuration file for Apache
that will be installed contains a valid configuration for HTTP basic
auth. The most conveniant way for you is to use the same user file as
for Nagios. Please enter your htpasswd file to use here"

ask_dir -d nagios_auth_name "Nagios Access" "Nagios Access" "OMD Monitoring Site $OMD_SITE" "HTTP AuthName" \
 "Check_mk's Apache configuration file will need an AuthName. That
string will be displayed to the user when asking for the password.
You should use the same AuthName as for Nagios. Otherwise the user will
have to log in twice"

# -------------------------------------------------------------------
ask_title "Integration with PNP4Nagios 0.6"
# -------------------------------------------------------------------

ask_dir pnptemplates /usr/share/$NAME/pnp-templates $HOMEBASEDIR/pnp-templates $OMD_ROOT/local/share/check_mk/pnp-templates "PNP4Nagios templates" \
  "Check_MK ships templates for PNP4Nagios for most of its checks.
Those templates make the history graphs look nice. PNP4Nagios
expects such templates in the directory pnp/templates in your
document root for static web pages"

ask_dir rrd_path /var/lib/nagios/rrd $HOMEBASEDIR/var/nagios/rrd $OMD_ROOT/var/pnp4nagios/perfdata "RRD files" \
    "Configure the directory PNP4Nagios stores the RRD database files in"

ask_dir rrdcached_socket /tmp/rrdcached.sock $HOMEBASEDIR/var/rrdcached.sock $OMD_ROOT/tmp/run/rrdached.sock "rrdcached socket" \
    "If you use the rrdcached to process performance data from Nagios,
you can configure the socket of the rrdcached here to make the prediction
feature use it"

# -------------------------------------------------------------------
ask_title "Check_MK Livestatus Module"
# -------------------------------------------------------------------

ask_dir -d enable_livestatus yes yes yes "compile livestatus module" \
  "The well known MK Livestatus broker module is part of Check_MK.

It provides direct access to Nagios internal data structures. It aims to
supersede status.dat and also NDO. The Livestatus Module does not only
allow extremely fast access to the status of your services and hosts, it
does also provide live data (which status.dat does not). Also - unlike NDO -
Livestatus does not cost you even measurable CPU performance, does not need
any disk space and also needs no configuration.

Livestatus is neccessary when you want to use Multisite. It is also
the preferred backend for NagVis.

Please answer 'yes', if you want to compile and integrate the
Livestatus module into your Nagios. You need 'make' and the GNU
C++ compiler installed in order to do this"

if [ "$enable_livestatus" = yes ]
then
  ask_dir -d nagios_version "3.5.0" "3.5.0" "OMD Monitoring Site $OMD_SITE" "Nagios / Icinga version" \
   "The version is required for the compilation of the livestatus module.
Depending on the major version (3 or 4) different nagios headers are included"

  ask_dir libdir /usr/lib/$NAME $HOMEBASEDIR/lib $OMD_ROOT/local/lib/mk-livestatus "check_mk's binary modules" \
   "Directory for architecture dependent binary libraries and plugins
of check_mk"

  ask_dir livesock ${nagpipe%/*}/live ${nagpipe%/*}/live $OMD_ROOT/tmp/run/live "Unix socket for Livestatus" \
   "The Livestatus Module provides Nagios status data via a unix
socket. This is similar to the Nagios command pipe, but allows
bidirectional communication. Please enter the path to that pipe.
It is recommended to put it into the same directory as Nagios'
command pipe"

  ask_dir livebackendsdir /usr/share/$NAME/livestatus $HOMEBASEDIR/livestatus $OMD_ROOT/local/share/mk-livestatus "Backends for other systems" \
   "Directory where to put backends and configuration examples for
other systems. Currently this is only Nagvis, but other might follow
later."
fi

# -------------------------------------------------------------------
ask_title "Check_MK Event Console"
# -------------------------------------------------------------------

ask_dir -d enable_mkeventd no no no "Install Event Console" \
  "The Check_MK Event Console is a full featured event processing
module that integrates with Multisite. It has an own daemon and
several methods for retrieving events. It even has an integrated
syslog daemon.  Please answer 'yes', if you want to enable the
Event Console."

if [ "$enable_mkeventd" = yes ]
then
  ask_dir mkeventdstatedir /var/lib/mkeventd $vardir/mkeventd $OMD_ROOT/var/mkeventd "working directory of mkeventd" \
  "The Event Console Daemon will store status and historic data in this
directory."
fi

if [ "$enable_mkeventd" = yes -a "$enable_livestatus" != yes ]
then
  ask_dir livesock ${nagpipe%/*}/live ${nagpipe%/*}/live $OMD_ROOT/tmp/run/live "Unix socket for Livestatus" \
   "The Livestatus Module provides Nagios status data via a unix
socket. This is similar to the Nagios command pipe, but allows
bidirectional communication. Please enter the path to that pipe.
It is recommended to put it into the same directory as Nagios'
command pipe"
fi

checksdir=$sharedir/checks
notificationsdir=$sharedir/notifications
inventorydir=$sharedir/inventory
web_dir=$sharedir/web
localedir=$sharedir/locale
agentsdir=$sharedir/agents
activechecksdir=${check_icmp_path%/*}

if [ -z "$YES" ]
then
    echo
    echo "----------------------------------------------------------------------"
    echo
    echo "You have chosen the following directories: "
    echo "$SUMMARY"
    echo
    echo
fi

propeller ()
{
   while read LINE
   do
      echo "$LINE"
      if [ -z "$YES" ] ; then echo -n "." >&2 ; fi
   done
}

compile_livestatus ()
{
   local D=$SRCDIR/livestatus.src
   rm -rf $D
   mkdir -p $D
   tar xvzf $SRCDIR/livestatus.tar.gz -C $D
   pushd $D

   local CONFIGURE_OPTS=""
   if [ -n "$nagios_version" ] ; then
        if [ ${nagios_version:0:1} == 4 ] ; then
           CONFIGURE_OPTS="--with-nagios4"
        fi
   fi
   ./configure --libdir=$libdir --bindir=$bindir $CONFIGURE_OPTS &&
   make clean &&
   cat <<EOF > src/livestatus.h &&
#ifndef livestatus_h
#define livestatus_h
#define DEFAULT_SOCKET_PATH "$livesock"
#endif // livestatus_h
EOF
   make -j 8  2>&1 &&
   strip src/livestatus.o &&
   mkdir -p $DESTDIR$libdir &&
   install -m 755 src/livestatus.o $DESTDIR$libdir &&
   mkdir -p $DESTDIR$bindir &&
   install -m 755 src/unixcat $DESTDIR$bindir &&
   popd
}

compile_mkeventd ()
{
   local D=$SRCDIR/bin
   rm -rf $D
   mkdir -p $D
   tar xzf $SRCDIR/bin.tar.gz -C $D
   pushd $D &&
   make &&
   popd
}

create_mkeventd_startscript ()
{
    if [ -e $DESTDIR/etc/init.d/mkeventd ] ; then return ; fi
    cat <<EOF > $DESTDIR/etc/init.d/mkeventd
#!/bin/sh

# chkconfig: 345 98 02
# description: Check_MK Event Console Daemon

### BEGIN INIT INFO
# Provides:       mkeventd
# Required-Start:
# Required-Stop:
# Default-Start:  2 3 5
# Default-Stop:
# Description:    Start Check_MK Event Console Daemon
### END INIT INFO

SOCKETDIR=$mkeventdsocketdir
DAEMON=$bindir/mkeventd
VARDIR=$mkeventdstatedir
CONFDIR=$confdir
MKEVENTD_SYSLOG=off
RUNUSER=$nagiosuser
LIVESTATUS=$livesock
# DEBUG="--debug --foreground"

PIDFILE=\$SOCKETDIR/pid
STATUS_SOCKET=\$SOCKETDIR/status
STATEFILE=\$VARDIR/status
OPTS="-C \$CONFDIR --statedir \$VARDIR --logdir \$VARDIR -P \$SOCKETDIR/events -E \$SOCKETDIR/eventsocket -S \$STATUS_SOCKET --pidfile \$PIDFILE \$DEBUG"
THE_PID=\$(cat \$PIDFILE 2>/dev/null)

case "\$1" in
    start)
        if [ "\$MKEVENTD_SYSLOG" = on ] ; then
            echo -n 'Starting mkeventd with integrated syslog...'
            if kill -0 \$THE_PID >/dev/null 2>&1; then
                echo 'Already running.'
                exit 0
            fi
            su -s /bin/sh - \$RUNUSER -c "\${DAEMON}_open514 --syslog --syslog-fd 3 \$OPTS"
        else
            echo -n 'Starting mkeventd...'
            if kill -0 \$THE_PID >/dev/null 2>&1; then
              echo 'Already running.'
              exit 0
            fi
            su -s /bin/sh - \$RUNUSER -c "\$DAEMON \$OPTS"
        fi
        echo OK
    ;;
    stop)
	echo -n 'Stopping mkeventd...'
        if [ -z "\$THE_PID" ] ; then
            echo 'Not running.'
        else
            echo -n "killing \$THE_PID..."
            kill \$THE_PID 2>/dev/null
            if [ \$? -eq 0 ]; then
                # Only wait for pidfile removal when the signal could be sent
                N=0
                while [ -e "\$PIDFILE" ] ; do
                    sleep 0.5
                    echo -n .
                    N=\$((N + 1))
                    if [ \$N -gt 20 ] ; then
                        echo "PID file did not vanish."
                        exit 1
                    fi
                done
            else
                # Remove the stale pidfile to have a clean state after this
                rm \$PIDFILE
            fi
            echo 'OK'
        fi
    ;;
    restart)
	\$0 stop && \$0 start
    ;;
    reload)
	echo -n 'Reloading mkeventd...'
        if [ -z "\$THE_PID" ] ; then
            echo 'Not running.'
            exit 1
        else
            echo "killing \$THE_PID with SIGHUP..."
            kill -1 \$THE_PID
        fi
    ;;

    status)
	echo -n 'Checking status of mkeventd...'
        if [ -z "\$THE_PID" ] ; then
            echo "not running (PID file missing)"
            exit 1
        elif ! kill -0 \$THE_PID ; then
            echo "not running (PID file orphaned)"
            exit 1
        else
            echo "running"
            exit 0
        fi
    ;;
    flush)
        if [ -n "\$THE_PID" ] && kill -0 \$THE_PID ; then
            echo -n "Flushing current state and history..."
            result=\$(echo "COMMAND FLUSH" | unixcat \$STATUS_SOCKET)
            if [ "\$result" = "None" ] ; then
                echo OK
                exit 0
            else
                echo "ERROR: \$result"
                exit 1
            fi
        else
            echo -n "Deleting status and history files..."
            rm -f \$VARDIR/{status,master_config,slave_status,history/*}
            echo OK
            exit 0
        fi
    ;;
    *)
	echo "Usage: \$0 {start|stop|restart|reload|status|flush}"
    ;;
esac
EOF
    chmod 755 $DESTDIR/etc/init.d/mkeventd
}


create_sudo_configuration ()
{
    # sudo only possible if running as root
    if [ $UID != 0 ] ; then
	return
    fi

    sudolines="Defaults:$wwwuser !requiretty\n$wwwuser ALL = (root) NOPASSWD: $bindir/check_mk --automation *"

    if [ ! -e /etc/sudoers ] ; then
        echo "You do not have sudo installed. Please install sudo "
        echo "and add the following line to /etc/sudoers if you want"
        echo "to use WATO - the Check_MK Web Administration Tool"
        echo
        echo -e "$sudolines"
        echo
        echo
        return
    fi

    if fgrep -q 'check_mk --automation' /etc/sudoers 2>/dev/null
    then
        # already present. Do not touch.
        return
    fi

    echo >> /etc/sudoers
    echo "# Needed for  WATO - the Check_MK Web Administration Tool" >> /etc/sudoers
    echo -e "$sudolines" >> /etc/sudoers
}

while true
do
    if [ -z "$DESTDIR" -a -z "$YES" ] ; then
        read -p "Proceed with installation (y/n)? " JA
    else
	JA=yes
    fi
    case "$JA" in
        j|J|ja|Ja|JA|y|yes|Y|Yes|YES)
	   # Save paths for later installation
	   if [ -z "$DESTDIR" ] ; then echo "$DIRINFO" > $SETUPCONF ; fi

	   if [ "$enable_livestatus" = yes ]
	   then
	       if [ -z "$YES" ] ; then echo -n "(Compiling MK Livestatus..." ; fi
	       compile_livestatus 2>&1 | propeller > $SRCDIR/livestatus.log
	       if [ "${PIPESTATUS[0]}" = 0 ]
	       then

		   if [ -z "$OMD_ROOT" -a "$livestatus_in_nagioscfg" = False -a -n "$DESTDIR$nagios_config_file" ]
		   then
			echo -e "# Load Livestatus Module\nbroker_module=$libdir/livestatus.o $livesock\nevent_broker_options=-1" \
			   >> $DESTDIR$nagios_config_file
                   elif [ "$OMD_ROOT" ] ; then
			echo -e "# Load Livestatus Module\nbroker_module=$OMD_ROOT/local/lib/mk-livestatus/livestatus.o pnp_path=$OMD_ROOT/var/pnp4nagios/perfdata $livesock\nevent_broker_options=-1" \
			   >> $OMD_ROOT/etc/mk-livestatus/nagios-local.cfg
			ln -sfn ../../mk-livestatus/nagios-local.cfg $OMD_ROOT/etc/nagios/nagios.d/mk-livestatus.cfg
		   fi
	       else
		   echo -e "\E[1;31;40m ERROR compiling livestatus! \E[0m.\nLogfile is in $SRCDIR/livestatus.log"
		   exit 1
	       fi
	       if [ -z "$YES" ] ; then echo ")" ; fi
	   fi &&
           mkdir -p $DESTDIR$sharedir &&
           mkdir -p $DESTDIR$python_lib_dir &&
           tar xzf $SRCDIR/lib.tar.gz -C $DESTDIR$python_lib_dir &&
           tar xzf $SRCDIR/base.tar.gz -C $DESTDIR$python_lib_dir &&
           mkdir -p $DESTDIR$sharedir/werks &&
           tar xzf $SRCDIR/werks.tar.gz -C $DESTDIR$sharedir/werks &&
           mkdir -p $DESTDIR$localedir &&
	   mkdir -p $DESTDIR$checksdir &&
	   tar xzf $SRCDIR/checks.tar.gz -C $DESTDIR$checksdir &&
	   mkdir -p $DESTDIR$activechecksdir &&
	   tar xzf $SRCDIR/active_checks.tar.gz -C $DESTDIR$activechecksdir &&
	   mkdir -p $DESTDIR$notificationsdir &&
	   tar xzf $SRCDIR/notifications.tar.gz -C $DESTDIR$notificationsdir &&
	   mkdir -p $DESTDIR$inventorydir &&
	   tar xzf $SRCDIR/inventory.tar.gz -C $DESTDIR$inventorydir &&
	   mkdir -p $DESTDIR$web_dir &&
	   tar xzf $SRCDIR/web.tar.gz -C $DESTDIR$web_dir &&
	   mkdir -p $DESTDIR$pnptemplates &&
	   tar xzf $SRCDIR/pnp-templates.tar.gz -C $DESTDIR$pnptemplates &&
	   mkdir -p $DESTDIR$docdir &&
	   tar xzf $SRCDIR/doc.tar.gz -C $DESTDIR$docdir &&
	   mkdir -p $DESTDIR$checkmandir &&
	   tar xzf $SRCDIR/checkman.tar.gz -C $DESTDIR$checkmandir &&
	   mkdir -p $DESTDIR$agentsdir &&
	   tar xzf $SRCDIR/agents.tar.gz -C $DESTDIR$agentsdir &&
	   for agent in $DESTDIR/$agentsdir/check_mk_*agent.* ; do
	       sed -ri 's@^export MK_LIBDIR="(.*)"@export MK_LIBDIR="'"$agentslibdir"'"@' $agent
	       sed -ri 's@^export MK_CONFDIR="(.*)"@export MK_CONFDIR="'"$agentsconfdir"'"@' $agent
	   done &&
	   mkdir -p $DESTDIR$vardir/{autochecks,counters,precompiled,cache,logwatch,web,wato,notify,log} &&
	   if [ -z "$DESTDIR" ] && id "$nagiosuser" > /dev/null 2>&1 && [ $UID = 0 ] ; then
	     chown -R $nagiosuser $DESTDIR$vardir/{counters,cache,logwatch,notify}
	     chown $nagiosuser $DESTDIR$vardir/{web,log}
           fi &&
	   mkdir -p $DESTDIR$confdir/conf.d &&
	   if [ -z "$DESTDIR" ] ; then
	     chgrp -R $wwwgroup $DESTDIR$vardir &&
	     chmod -R g+w $DESTDIR$vardir &&
	     chgrp -R $wwwgroup $DESTDIR$vardir/web &&
	     chmod -R g+w $DESTDIR$vardir/web &&
	     chgrp -R $wwwgroup $DESTDIR$vardir/log &&
	     chmod -R g+w $DESTDIR$vardir/log &&
	     chgrp -R $wwwgroup $DESTDIR$vardir/wato &&
	     chmod -R g+w $DESTDIR$vardir/wato
             mkdir -p $DESTDIR$vardir/tmp &&
	     chgrp -R $wwwgroup $DESTDIR$vardir/tmp &&
             chmod g+w $DESTDIR$vardir/tmp &&
             mkdir -p $DESTDIR$confdir/conf.d/wato &&
             chmod -R g+w $DESTDIR$confdir/conf.d/wato &&
             chgrp -R $wwwgroup $DESTDIR$confdir/conf.d/wato
             mkdir -p $DESTDIR$confdir/multisite.d/wato &&
             chmod -R g+w $DESTDIR$confdir/multisite.d/wato &&
             chgrp -R $wwwgroup $DESTDIR$confdir/multisite.d/wato
             touch $DESTDIR$confdir/multisite.d/sites.mk &&
             chgrp $wwwgroup $DESTDIR$confdir/multisite.d/sites.mk &&
             chmod 664 $DESTDIR$confdir/multisite.d/sites.mk &&
             touch $DESTDIR$confdir/conf.d/distributed_wato.mk &&
             chgrp $wwwgroup $DESTDIR$confdir/conf.d/distributed_wato.mk &&
             chmod 664 $DESTDIR$confdir/conf.d/distributed_wato.mk
	   fi &&
           echo -e "# Main configuration file of Check_MK\n#We highly recommend to use WATO to configure Check_MK these days." \
               > $DESTDIR$confdir/main.mk-$VERSION &&
           echo -e "# Main configuration file of the Check_MK GUI\n#We highly recommend to use WATO to configure Check_MK these days." \
               > $DESTDIR$confdir/multisite.mk-$VERSION &&
	   if [ -e $DESTDIR$confdir/check_mk.cfg -a ! -e $DESTDIR$confdir/main.mk ] ; then
	       mv -v $DESTDIR$confdir/check_mk.cfg $DESTDIR$confdir/main.mk
               echo "Renamed check_mk.cfg into main.mk."
           fi &&
	   for f in $DESTDIR$vardir/autochecks/*.cfg $DESTDIR$confdir/conf.d/*.cfg ; do
	       if [ -e "$f" ] ; then
		   mv -v $f ${f%.cfg}.mk
               fi
           done &&
	   if [ ! -e $DESTDIR$confdir/main.mk ] ; then
	      cp $DESTDIR$confdir/main.mk-$VERSION $DESTDIR$confdir/main.mk
           fi &&
	   if [ ! -e $DESTDIR$confdir/multisite.mk ] ; then
	      cp $DESTDIR$confdir/multisite.mk-$VERSION $DESTDIR$confdir/multisite.mk
           fi &&
           mkdir -p $DESTDIR$confdir/multisite.d &&
	   mkdir -p $DESTDIR$confdir/conf.d &&
	   echo 'All files in this directory that end with .mk will be read in after main.mk' > $DESTDIR$confdir/conf.d/README &&
           mkdir -p "$DESTDIR$nagconfdir"
	   if [ ! -e $DESTDIR$nagconfdir/check_mk_templates.cfg ] ; then
 	       ln -s $sharedir/check_mk_templates.cfg $DESTDIR$nagconfdir 2>/dev/null
	   fi
	   if [ -n "$nagiosaddconf" -a -n "$DESTDIR$nagios_config_file" ] ; then
	      echo "# added by setup.sh of check_mk " >> $DESTDIR$nagios_config_file
	      echo "$nagiosaddconf" >> $DESTDIR$nagios_config_file
	   fi &&

           mkdir -p $DESTDIR$vardir/packages &&
           install -m 644 $SRCDIR/package_info $DESTDIR$vardir/packages/check_mk &&

	   mkdir -p $DESTDIR$apache_config_dir &&
	   if [ ! -e $DESTDIR$apache_config_dir/$NAME -a ! -e $DESTDIR$apache_config_dir/zzz_$NAME.conf -a -z "$OMD_ROOT" ]
	   then
	       cat <<EOF > $DESTDIR$apache_config_dir/zzz_$NAME.conf
# Created by setup of check_mk version $VERSION
# This file will *not* be overwritten at the next setup
# of check_mk. You may edit it as needed. In order to get
# a new version, please delete it and re-run setup.sh.

# Note for RedHat 5.3 users (and probably other version:
# this file must be loaded *after* python.conf, otherwise
# <IfModule mod_python.c> does not trigger! For that
# reason, it is installed as zzz_.... Sorry for the
# inconveniance.

<IfModule mod_python.c>
  Alias ${url_prefix}check_mk $web_dir/htdocs
  <Directory $web_dir/htdocs>
        AddHandler mod_python .py
        PythonHandler index
        PythonDebug Off
	DirectoryIndex index.py

	# Need Nagios authentification. Please edit the
	# following: Set AuthName and AuthUserFile to the
	# same value that you use for your Nagios configuration!
        Order deny,allow
        allow from all
	AuthName "$nagios_auth_name"
        AuthType Basic
        AuthUserFile $htpasswd_file
        require valid-user

	ErrorDocument 403 "<h1>Authentication Problem</h1>\
Either you've entered an invalid password or the authentication<br>\
configuration of your check_mk web pages is incorrect.<br><br>\
Please make sure that you've edited the file<br>\
<tt>$apache_config_dir/$NAME</tt> and made it use the same<br>\
authentication settings as your Nagios web pages.<br>\
Restart Apache afterwards."
	ErrorDocument 500 "<h1>Server or Configuration Problem</h1>\
A Server problem occurred. You'll find details in the error log of \
Apache. One possible reason is, that the file <tt>$htpasswd_file</tt> \
is missing. You can create that file with <tt>htpasswd</tt> or \
<tt>htpasswd2</tt>. A better solution might be to use your existing \
htpasswd file from your Nagios installation. Please edit <tt>$apache_config_dir/$NAME</tt> \
and change the path there. Restart Apache afterwards."
  </Directory>
  # Automation is done without HTTP Auth
  <Location "${url_prefix}check_mk/automation.py">
       Order allow,deny
       Allow from all
       Satisfy any
  </Location>

  # Trigger cron jobs. This is done without authentication
  <Location "${url_prefix}check_mk/run_cron.py">
      Order deny,allow
      Deny from all
      Allow from 127.0.0.1
      Satisfy any
  </Location>

  # Webservice for dynamic creation of PNP templates
  <Location "${url_prefix}check_mk/pnp_template.py">
      Order deny,allow
      Deny from all
      Allow from 127.0.0.1
      Satisfy any
  </Location>

</IfModule>



<IfModule !mod_python.c>
  Alias ${url_prefix}check_mk $web_dir/htdocs
  <Directory $web_dir/htdocs>
        Deny from all
        ErrorDocument 403 "<h1>Check_mk: Incomplete Apache2 Installation</h1>\
You need mod_python in order to run the web interface of check_mk.<br> \
Please install mod_python and restart Apache."
  </Directory>
</IfModule>
EOF
           fi &&
	   for d in $DESTDIR$apache_config_dir/../*/*$NAME{,.conf} ; do
	       if [ -e "$d" ] && ! grep -q "$web_dir/htdocs" $d ; then
		   echo "Changing $web_dir to $web_dir/htdocs in $d"
		   sed -i "s@$web_dir@$web_dir/htdocs@g" $d
	       fi
	   done &&
           # make htpasswd writable by apache, since we need this for
           # WATO. Also create an empty and Apache-writable auth.serials
           serials_file=$DESTDIR${htpasswd_file%/*}/auth.serials &&
           touch "$serials_file" &&
	   create_sudo_configuration &&
           if [ "$enable_mkeventd" = yes ]
           then
	       if [ -z "$YES" ] ; then echo -n "(Compiling Event Console binaries..." ; fi
	       compile_mkeventd 2>&1 | propeller > $SRCDIR/mkeventd.log
	       if [ "${PIPESTATUS[0]}" = 0 ]
	       then
                   pushd $SRCDIR > /dev/null &&
                   install -m 755 bin/mkevent bin/mkeventd $DESTDIR$bindir &&
                   install -m 750 bin/mkeventd_open514 -g $wwwgroup $DESTDIR$bindir &&
	           setcap "cap_net_bind_service+ep" $DESTDIR$bindir/mkeventd_open514  &&
                   mkdir -p $DESTDIR$confdir/mkeventd.d/wato &&
                   if [ ! -e "$DESTDIR$confdir/multisite.d/mkeventd.mk" ] ; then
                       mkdir -p $DESTDIR$confdir/multisite.d &&
                       echo 'mkeventd_enabled = True' > $DESTDIR$confdir/multisite.d/mkeventd.mk
                   fi &&
                   touch $DESTDIR$confdir/mkeventd.mk &&
                   mkeventdsocketdir=${livesock%/*}/mkeventd &&
                   mkdir -p $DESTDIR$mkeventdsocketdir &&
                   chown $nagiosuser.$wwwgroup $DESTDIR$mkeventdsocketdir &&
                   chmod 2755 $DESTDIR$mkeventdsocketdir &&
                   mkdir -p $DESTDIR$mkeventdstatedir &&
                   chown $nagiosuser $DESTDIR$mkeventdstatedir &&
                   create_mkeventd_startscript &&
                   popd > /dev/null
	       else
		   echo -e "\E[1;31;40m ERROR compiling Event Console binaries! \E[0m.\nLogfile is in $SRCDIR/mkeventd.log"
		   exit 1
	       fi
	       if [ -z "$YES" ] ; then echo ")" ; fi
           fi &&
	   if [ -z "$YES" ] ; then
	       echo -e "Installation completed successfully.\nPlease restart Nagios and Apache in order to update/active check_mk's web pages."
	       echo
	       echo -e "You can access the new Multisite GUI at http://localhost${url_prefix}check_mk/"
           fi ||
               ( echo "ERROR!" ; exit 1 )
	   exit
        ;;
        n|N|no|No|Nein|nein)
        echo "Aborted."
        exit 1
        ;;
    esac
done
