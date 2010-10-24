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


VERSION=1.1.8
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
    SHORT=$4
    DESCR=$5

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
	    if [ "$ROOT" ] ; then
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

if [ -z "$YES" ] ; then cat <<EOF


[1;44;37m                  _               _                  _                  [0m
[1;44;37m              ___| |__   ___  ___| | __    _ __ ___ | | __              [0m
[1;44;37m             / __| '_ \ / _ \/ __| |/ /   | '_ \` _ \| |/ /              [0m
[1;44;37m            | (__| | | |  __/ (__|   <    | | | | | |   <               [0m
[1;44;37m             \___|_| |_|\___|\___|_|\_\___|_| |_| |_|_|\_\              [0m
[1;44;37m                                     |_____|                            [0m
[1;44;37m                                                                        [0m
[1;45;37m   check_mk setup                  $(printf "%32s" Version:' '$VERSION)     [0m


Welcome to check_mk. This setup will install check_mk into user defined
directories. If you run this script as root, installation paths below
/usr will be suggested. If you run this script as non-root user paths
in your home directory will be suggested. You may override the default
values or just hit enter to accept them. 

Your answers will be saved to $SETUPCONF and will be 
reused when you run the setup of this or a later version again. Please
delete that file if you want to delete your previous answers.

EOF
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

ask_dir bindir /usr/bin $HOMEBASEDIR/bin "Executable programs" \
  "Directory where to install executable programs such as check_mk itself.
This directory should be in your search path (\$PATH). Otherwise you
always have to specify the installation path when calling check_mk"

ask_dir confdir /etc/$NAME $HOMEBASEDIR "check_mk configuration" \
  "Directory where check_mk looks for its main configuration file main.mk. 
An example configuration file will be installed there if no main.mk is 
present from a previous version."

ask_dir checksdir /usr/share/$NAME/checks $HOMEBASEDIR/checks "check_mk checks" \
  "check_mk's different checks are implemented as small Python scriptlets 
that parse and interpret the various output sections of the agents. Where 
shall those be installed"

ask_dir modulesdir /usr/share/$NAME/modules $HOMEBASEDIR/modules "check_mk modules" \
  "Directory for main componentents of check_mk itself. The setup will
also create a file 'defaults' in that directory that reflects all settings
you are doing right now" 

ask_dir web_dir /usr/share/$NAME/web $HOMEBASEDIR/web "check_mk's web pages" \
  "Directory where Check_mk's web pages should be installed. Currently these
web pages allow you to search in all of Nagios services and send several
different commands to all found services. That directory should [4;1mnot[0m be
in your WWW document root. A separate apache configuration file will be
installed that maps the directory into your URL schema"

ask_dir mibsdir /usr/share/snmp/mibs $HOMEBASEDIR/mibs "SNMP mibs" \
  "Directory for SNMP MIB files (for copyright reasons we currently do
not ship any MIB files, though...)" 

ask_dir docdir /usr/share/doc/$NAME $HOMEBASEDIR/doc "documentation" \
  "Some documentation about check_mk will be installed here. Please note,
however, that most of check_mk's documentation is available only online at
http://mathias-kettner.de/check_mk.html"

ask_dir checkmandir /usr/share/doc/$NAME/checks $HOMEBASEDIR/doc/checks "check manuals" \
  "Directory for manuals for the various checks. The manuals can be viewed 
with check_mk -M <CHECKNAME>"

ask_dir vardir /var/lib/$NAME $HOMEBASEDIR/var "working directory of check_mk" \
  "check_mk will create caches files, automatically created checks and
other files into this directory. The setup will create several subdirectories
and makes them writable by the Nagios process"

ask_dir agentsdir /usr/share/$NAME/agents $HOMEBASEDIR/agents "agents for operating systems" \
  "Agents for various operating systems will be installed here for your 
conveniance. Take them and install them onto your target hosts"

ask_title "Configuration of Linux/UNIX Agents"


ask_dir agentslibdir /usr/lib/check_mk_agent $HOMEBASEDIR/check_mk_agent "extensions for agents" \
  "This directory will not be created on the server. It will be hardcoded 
into the Linux and UNIX agents. The agent will look for extensions in the 
subdirectories plugins/ and local/ of that directory"

ask_dir agentsconfdir /etc/check_mk $HOMEBASEDIR "configuration dir for agents" \
  "This directory will not be created on the server. It will be hardcoded
into the Linux and UNIX agents. The agent will look for its configuration
files here (currently only the logwatch extension needs a configuration file)"

ask_title "Integration with Nagios"

ask_dir -d nagiosuser nagios $(id -un) "Name of Nagios user" \
  "The working directory for check_mk contains several subdirectories
that need to be writable by the Nagios user (which is running check_mk 
in check mode). Please specify the user that should own those 
directories"

ask_dir -d wwwgroup nagios $(id -un) "Common group of Nagios+Apache" \
  "Check_mk creates files and directories while running as $nagiosuser. 
Some of those need to be writable by the user that is running the webserver.
Therefore a group is needed in which both Nagios and the webserver are
members (every valid Nagios installation uses such a group to allow
the web server access to Nagios' command pipe):"

ask_dir nagios_binary /usr/sbin/nagios $HOMEBASEDIR/nagios/bin/nagios "Nagios binary" \
  "The complete path to the Nagios executable. This is needed by the
option -R/--restart in order to do a configuration check."

ask_dir nagios_config_file /etc/nagios/nagios.cfg $HOMEBASEDIR/nagios/etc/nagios.cfg "Nagios main configuration file" \
  "Path to the main configuration file of Nagios. That file is always 
named 'nagios.cfg'. The default path when compiling Nagios yourself
is /usr/local/nagios/etc/nagios.cfg. The path to this file is needed
for the check_mk option -R/--restart"

ask_dir nagconfdir /etc/nagios/objects $HOMEBASEDIR/nagios/etc "Nagios object directory" \
  "Nagios' object definitions for hosts, services and contacts are
usually stored in various files with the extension .cfg. These files
are located in a directory that is configured in nagios.cfg with the
directive 'cfg_dir'. Please specify the path to that directory 
(If the autodetection can find your configuration
file but does not find at least one cfg_dir directive, then it will
add one to your configuration file for your conveniance)"

ask_dir nagios_startscript /etc/init.d/nagios /etc/init.d/nagios "Nagios startskript" \
  "The complete path to the Nagios startskript is used by the option
-R/--restart to restart Nagios."

ask_dir -d nagiosurl /nagios /nagios "Base URL of website" \
  "The configuration files generated by check_mk contain some
HTTP links to Nagios web pages. Please enter the correct base
URL of your Nagios pages. The trailing slash will be appended by check_mk"

ask_dir -d cgiurl /nagios/cgi-bin /nagios/cgi-bin "Base URL of cgi programs" \
  "The Nagios cgi programs have their own base URL. If you are
unsure then hower your mouse over a link to host or status 
data and look at your browser's status line. Leave out the
host name and also the 'status.cgi?...'"

ask_dir nagpipe /var/log/nagios/rw/nagios.cmd /var/log/nagios/rw/nagios.cmd "Nagios command pipe" \
  "Complete path to the Nagios command pipe. check_mk needs write access
to this pipe in order to operate"

ask_dir nagios_status_file /var/log/nagios/status.dat /var/log/nagios/status.dat "Nagios status file" \
  "The web pages of check_mk need to read the file 'status.dat', which is
regularily created by Nagios. The path to that status file is usually
configured in nagios.cfg with the parameter 'status_file'. If
that parameter is missing, a compiled-in default value is used. On
FHS-conforming installations, that file usually is in /var/lib/nagios
or /var/log/nagios. If you've compiled Nagios yourself, that file
might be found below /usr/local/nagios"

ask_dir check_icmp_path /usr/lib/nagios/plugins/check_icmp $HOMEBASEDIR/libexec/check_icmp "Path to check_icmp" \
  "check_mk ships a Nagios configuration file with several host and
service templates. Some host templates need check_icmp as host check.
That check plugin is contained in the standard Nagios plugins.
Please specify the complete path (dir + filename) of check_icmp"

ask_title "Integration with Apache"

ask_dir checkmk_web_uri /check_mk /check_mk "Check_mk web URI" \
 "Please enter the URI to the check_mk web pages here. The uri must
begin with a slash. You can point your browser to that uri on your
Nagios host and will reach check_mk's web pages. Please not that
you need mod_python in order for the check_mk web pages to work."

ask_dir apache_config_dir /etc/apache2/conf.d /etc/apache2/conf.d "Apache config dir" \
 "Check_mk ships several web pages implemented in Python with Apache
mod_python. That module needs an apache configuration section which
will be installed by this setup. Please specify the path to a directory
where Apache reads in configuration files."

ask_dir htpasswd_file /etc/nagios/htpasswd.users $HOMEBASEDIR/etc/htpasswd.users "HTTP authentication file" \
 "Check_mk's web pages should be secured from unauthorized access via
HTTP authenticaion - just as Nagios. The configuration file for Apache
that will be installed contains a valid configuration for HTTP basic
auth. The most conveniant way for you is to use the same user file as
for Nagios. Please enter your htpasswd file to use here"

ask_dir -d nagios_auth_name "Nagios Access" "Nagios Access" "HTTP AuthName" \
 "Check_mk's Apache configuration file will need an AuthName. That
string will be displayed to the user when asking for the password.
You should use the same AuthName as for Nagios. Otherwise the user will 
have to log in twice"

# -------------------------------------------------------------------
ask_title "Integration with PNP4Nagios 0.6"
# -------------------------------------------------------------------

ask_dir -d pnp_url /pnp4nagios/ /pnp4nagios/ "URL prefix for PNP4Nagios" \
  "Check_MK automatically creates links to PNP4Nagios for hosts and
services which have performance data. And Multisite supports PNP by
creating links in inline performance graphs. Please specify the URL
to your installation of PNP4Nagios including the trailing slash if
you want to use PNP integration (Note: PNP 0.4 is not supported any
longer)"

ask_dir rrddir $vardir/rrd $vardir/rrd "round robin databases" \
  "Base directory for round robin databases. If you use PNP4Nagios as
graphing tool check_mk can directly write into the exsting databases.
This saves CPU and disk IO"

ask_dir pnptemplates /usr/share/$NAME/pnp-templates $HOMEBASEDIR/pnp-templates "PNP4Nagios templates" \
  "Check_MK ships templates for PNP4Nagios for most of its checks.
Those templates make the history graphs look nice. PNP4Nagios
expects such templates in the directory pnp/templates in your
document root for static web pages"

ask_dir pnprraconf /usr/share/$NAME/pnp-rraconf $HOMEBASEDIR/pnp-rraconf "RRA configuration for PNP4Nagios" \
  "Check_MK ships RRA configuration files for its checks that 
can be used by PNP when creating the RRDs. Per default, PNP 
creates RRD such that for each variable the minimum, maximum
and average value is stored. Most checks need only one or two
of these aggregations. If you install the Check_MK's RRA config
files into the configuration directory of PNP, PNP will create
RRDs with the minimum of required aggregation and thus save
substantial amount of disk I/O (and space) for RRDs. The default
is to install the configuration into a separate directory but
does not enable them"

# -------------------------------------------------------------------
ask_title "Check_MK Livestatus Module"
# -------------------------------------------------------------------

ask_dir -d enable_livestatus yes yes "compile livestatus module" \
  "This version of Check_mk ships a completely new and experimental
Nagios event broker module that provides direct access to Nagios
internal data structures. This module is called the Check_MK Livestatus
Module. It aims to supersede status.dat and also NDO. Currenty it
is completely experimental and might even crash your Nagios process.
Nevertheless - The Livestatus Module does not only allow extremely
fast access to the status of your services and hosts, it does also
provide live data (which status.dat does not). Also - unlike NDO - 
Livestatus does not cost you even measurable CPU performance, does
not need any disk space and also needs no configuration. 

Please answer 'yes', if you want to compile and integrate the
Livestatus module into your Nagios. You need 'make' and the GNU
C++ compiler installed in order to do this"

if [ "$enable_livestatus" = yes ]
then
  ask_dir libdir /usr/lib/$NAME $HOMEBASEDIR/lib "check_mk's binary modules" \
   "Directory for architecture dependent binary libraries and plugins
of check_mk"

  ask_dir livesock ${nagpipe%/*}/live ${nagpipe%/*}/live "Unix socket for Livestatus" \
   "The Livestatus Module provides Nagios status data via a unix
socket. This is similar to the Nagios command pipe, but allows
bidirectional communication. Please enter the path to that pipe.
It is recommended to put it into the same directory as Nagios'
command pipe"

  ask_dir livebackendsdir /usr/share/$NAME/livestatus $HOMEBASEDIR/livestatus "Backends for other systems" \
   "Directory where to put backends and configuration examples for
other systems. Currently this is only Nagvis, but other might follow
later."
fi


create_defaults ()
{
cat <<EOF
# This file has been created during setup of check_mk at $(date).
# Do not edit this file. Also do not try to override these settings
# in main.mk since some of them are hardcoded into several files
# during setup. 
#
# If you need to change these settings, you have to re-run setup.sh
# and enter new values when asked, or edit ~/.check_mk_setup.conf and
# run ./setup.sh --yes.

check_mk_version            = '$VERSION'
default_config_dir          = '$confdir'
check_mk_configdir          = '$confdir/conf.d'
checks_dir                  = '$checksdir'
check_manpages_dir          = '$checkmandir'
modules_dir                 = '$modulesdir'
agents_dir                  = '$agentsdir'
var_dir                     = '$vardir'
lib_dir                     = '$libdir'
snmpwalks_dir               = '$vardir/snmpwalks'
autochecksdir               = '$vardir/autochecks'
precompiled_hostchecks_dir  = '$vardir/precompiled'
counters_directory          = '$vardir/counters'
tcp_cache_dir		    = '$vardir/cache'
logwatch_dir                = '$vardir/logwatch'
nagios_objects_file         = '$nagconfdir/check_mk_objects.cfg'
rrd_path                    = '$rrddir'
nagios_command_pipe_path    = '$nagpipe'
nagios_status_file          = '$nagios_status_file'
nagios_conf_dir             = '$nagconfdir'
nagios_user                 = '$nagiosuser'
nagios_url                  = '$nagiosurl'
nagios_cgi_url              = '$cgiurl'
logwatch_notes_url          = '$checkmk_web_uri/logwatch.py?host=%s&file=%s'
www_group                   = '$wwwgroup'
nagios_config_file          = '$nagios_config_file'
nagios_startscript          = '$nagios_startscript'
nagios_binary               = '$nagios_binary'
apache_config_dir           = '$apache_config_dir'
htpasswd_file               = '$htpasswd_file'
nagios_auth_name            = '$nagios_auth_name'
web_dir                     = '$web_dir'
checkmk_web_uri             = '$checkmk_web_uri'
livestatus_unix_socket      = '$livesock'
livebackendsdir             = '$livebackendsdir'
pnp_url                     = '$pnp_url'
pnp_templates_dir           = '$pnptemplates'
pnp_rraconf_dir             = '$pnprraconf'
doc_dir                     = '$docdir'
EOF
}


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
   ./configure --libdir=$libdir --bindir=$bindir &&
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
   install -m 755 src/livestatus.o $DESTDIR$libdir/livestatus.o &&
   mkdir -p $DESTDIR$bindir &&
   install -m 755 src/unixcat $DESTDIR$bindir &&
   popd 
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

		   if [ "$livestatus_in_nagioscfg" = False -a -n "$DESTDIR$nagios_config_file" ]
		   then
			echo -e "# Load Livestatus Module\nbroker_module=$libdir/livestatus.o $livesock\nevent_broker_options=-1" \
			   >> $DESTDIR$nagios_config_file
		   fi
	       else
		   echo -e "\E[1;31;40m ERROR compiling livestatus! \E[0m.\nLogfile is in $SRCDIR/livestatus.log"
		   exit 1
	       fi
	       if [ -z "$YES" ] ; then echo ")" ; fi
	   fi &&
	   mkdir -p $DESTDIR$modulesdir &&
	   create_defaults > $DESTDIR$modulesdir/defaults &&
	   mkdir -p $DESTDIR$checksdir &&
	   tar xzf $SRCDIR/checks.tar.gz -C $DESTDIR$checksdir &&
	   mkdir -p $DESTDIR$web_dir &&
	   tar xzf $SRCDIR/web.tar.gz -C $DESTDIR$web_dir &&
	   cp $DESTDIR$modulesdir/defaults $DESTDIR$web_dir/htdocs/defaults.py &&
	   mkdir -p $DESTDIR$pnptemplates &&
	   tar xzf $SRCDIR/pnp-templates.tar.gz -C $DESTDIR$pnptemplates &&
	   mkdir -p $DESTDIR$pnprraconf &&
	   tar xzf $SRCDIR/pnp-rraconf.tar.gz -C $DESTDIR$pnprraconf &&
	   mkdir -p $DESTDIR$modulesdir &&
	   rm -f $DESTDIR$modulesdir/check_mk{,_admin} &&
	   tar xzf $SRCDIR/modules.tar.gz -C $DESTDIR$modulesdir &&
	   mkdir -p $DESTDIR$docdir &&
	   tar xzf $SRCDIR/doc.tar.gz -C $DESTDIR$docdir &&
	   mkdir -p $DESTDIR$checkmandir &&
	   tar xzf $SRCDIR/checkman.tar.gz -C $DESTDIR$checkmandir &&
	   if [ -e $SRCDIR/mibs.tar.gz ] ; then 
	       mkdir -p $DESTDIR$mibsdir &&
	       tar xzf $SRCDIR/mibs.tar.gz -C $DESTDIR$mibsdir
	   fi &&
	   mkdir -p $DESTDIR$agentsdir &&
	   tar xzf $SRCDIR/agents.tar.gz -C $DESTDIR$agentsdir &&
	   for agent in $DESTDIR/$agentsdir/check_mk_*agent.* $DESTDIR/$agentsdir/mk_logwatch ; do 
	       sed -ri 's@^export MK_LIBDIR="(.*)"@export MK_LIBDIR="'"$agentslibdir"'"@' $agent 
	       sed -ri 's@^export MK_CONFDIR="(.*)"@export MK_CONFDIR="'"$agentsconfdir"'"@' $agent 
	   done &&
	   mkdir -p $DESTDIR$vardir/{autochecks,counters,precompiled,cache,logwatch,web} &&
	   if [ -z "$DESTDIR" ] && id "$nagiosuser" > /dev/null 2>&1 && [ $UID = 0 ] ; then
	     chown -R $nagiosuser $DESTDIR$vardir/{counters,cache,logwatch}
	     chown $nagiosuser $DESTDIR$vardir/web
           fi &&
	   if [ -z "$DESTDIR" ] ; then
	     chgrp -R $wwwgroup $DESTDIR$vardir/web &&
	     chmod -R g+w $DESTDIR$vardir/web
	   fi &&
	   mkdir -p $DESTDIR$confdir/conf.d && 
	   tar xzf $SRCDIR/conf.tar.gz -C $DESTDIR$confdir &&
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
	   mkdir -p $DESTDIR$confdir/conf.d &&
	   echo 'All files in this directory that end with .mk will be read in after main.mk' > $DESTDIR$confdir/conf.d/README &&
	   if [ ! -d $DESTDIR$rrddir ] ; then
	       mkdir -p $DESTDIR$rrddir && 
	       if [ -z "$DESTDIR" ] && id "$nagiosuser" > /dev/null 2>&1 && [ $UID = 0 ] ; then
		   chown $nagiosuser $DESTDIR$rrddir
               fi
	   fi &&
	   mkdir -p $DESTDIR$bindir &&
	   rm -f $DESTDIR$bindir/check_mk &&
	   echo -e "#!/bin/sh\nexec python $modulesdir/check_mk.py "'"$@"' > $DESTDIR$bindir/check_mk
	   chmod 755 $DESTDIR$bindir/check_mk &&
	   sed -i "s#@BINDIR@#$bindir#g"              $DESTDIR$docdir/check_mk_templates.cfg &&
	   sed -i "s#@VARDIR@#$vardir#g"              $DESTDIR$docdir/check_mk_templates.cfg &&
	   sed -i "s#@CGIURL@#$cgiurl#g"              $DESTDIR$docdir/check_mk_templates.cfg &&
	   sed -i "s#@CHECK_ICMP@#$check_icmp_path#g" $DESTDIR$docdir/check_mk_templates.cfg &&
	   sed -i "s#@NAGIOSURL@#$nagiosurl#g"        $DESTDIR$docdir/check_mk_templates.cfg &&
	   sed -i "s#@PNPURL@#$pnp_url#g"             $DESTDIR$docdir/check_mk_templates.cfg &&
           mkdir -p "$DESTDIR$nagconfdir"
	   if [ ! -e $DESTDIR$nagconfdir/check_mk_templates.cfg ] ; then
 	       ln -s $docdir/check_mk_templates.cfg $DESTDIR$nagconfdir 2>/dev/null
	   fi
	   if [ -n "$nagiosaddconf" -a -n "$DESTDIR$nagios_config_file" ] ; then
	      echo "# added by setup.sh of check_mk " >> $DESTDIR$nagios_config_file
	      echo "$nagiosaddconf" >> $DESTDIR$nagios_config_file
	   fi &&

           mkdir -p $DESTDIR$vardir/packages &&
           install -m 644 package_info $DESTDIR$vardir/packages/check_mk &&

	   mkdir -p $DESTDIR$apache_config_dir &&
	   if [ ! -e $DESTDIR$apache_config_dir/$NAME -a ! -e $DESTDIR$apache_config_dir/zzz_$NAME.conf ]
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
  Alias $checkmk_web_uri $web_dir/htdocs
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
</IfModule>

<IfModule !mod_python.c>
  Alias $checkmk_web_uri $web_dir/htdocs
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
	   if [ -z "$YES" ] ; then
	       echo -e "Installation completed successfully.\nPlease restart Nagios and Apache in order to update/active check_mk's web pages."
	       echo
	       echo -e "You can access the new Multisite GUI at http://localhost$checkmk_web_uri/"
           fi ||
	   echo "ERROR!"
	   exit
        ;;
        n|N|no|No|Nein|nein)
        echo "Aborted."
        exit 1
        ;;
    esac
done
