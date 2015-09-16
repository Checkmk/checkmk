#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
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

import os, sys, stat

opt_debug = "-d" in sys.argv or "--debug" in sys.argv

# The following settings are tried to be autodetected
target_values = {
    'apache_config_dir' : "Configuration directory of Apache",
    'cgiurl'            : "URL of Nagios CGI programs",
    'check_icmp_path'   : "Path to check_icmp Plugin",
    'htdocsdir'         : "Directory of Nagios' static web pages",
    'htpasswd_file'     : "File of Nagios' HTTP users and passwords",
    'livestatus_in_nagioscfg' : "Wether nagios.cfg loads livestatus module",
    'nagconfdir'        : "Directory of Nagios objects (see cfg_dir)",
    'nagiosaddconf'     : "Snippet to add to nagios.cfg",
    'nagios_auth_name'  : "HTTP Basic AuthName for Nagios",
    'nagios_binary'     : "Absolute path to Nagios binary itself",
    'nagios_version'    : "Nagios version",
    'nagios_config_file': "Absolute path to nagios.cfg",
    'nagios_startscript': "Nagios startskript (usually in /etc/init.d)",
    'nagios_status_file': "Absolute path to Nagios' status.dat",
    'nagiosurl'         : "Base-URL of Nagios web pages",
    'nagiosuser'        : "System user running the Nagios process",
    'nagpipe'           : "Absolute path to Nagios' command pipe (nagios.cmd)",
    'check_result_path' : "Absolute path to Nagios' checkresults directory",
    'pnp_url'           : "URL of PNP4Nagios",
    'pnpconffile'       : "PNP4Nagios configuration file for its PHP pages",
    'pnphtdocsdir'      : "PNP4Nagios www document root directory",
    'pnptemplates'      : "directory of PHP templates for PNP4Nagios",
    'rrddir'            : "Base directory where RRDs are stored",
    'wwwgroup'          : "Common group of Nagios and Apache",
    'wwwuser'           : "System user apache runs with",
}

# Ich suche nach Prozessen mit folgenden Kriterien:
# - Der Text 'nagios' im Namen
# - eines der Worte muss '-d' oder '--daemon' sein.
# - Das letzte Wort ist der Name einer existierenden Datei
# Beispiel:
# /usr/sbin/nagios3 -d /etc/nagios3/nagios.cfg

class Sorry(Exception):
    def __init__(self, text):
        self.reason = text

def find_pid_and_configfile():
    procs = os.popen("ps ax -o pid,ppid,user,command").readlines()
    pids = []
    for line in procs:
        if line.find('nagios.cfg') >= 0 or line.find('icinga.cfg') >= 0:
            pids.append(line.split()[0])

    for line in procs:
        if line.find('nagios.cfg') >= 0 or line.find('icinga.cfg') >= 0:
            try:
                words = line.split()
                if '-d' in words or '--daemon' in words:
                    pid        = words[0]
                    ppid       = words[1]
                    user       = words[2]
                    configfile = words[-1]
                    if ppid in pids:
                        continue # this is not the main thread. It has
                                 # another process as parent!
                    if os.path.exists(configfile):
                        return int(pid), user, configfile
            except Exception, e:
                if opt_debug:
                    raise

    raise Sorry("Cannot find Nagios/Icinga process. Is it running?")

def find_apache_properties(nagiosuser, nagios_htdocs_dir):
    wwwuser = None

    # Search in running processes for Apache
    for line in os.popen("ps ax -o pid,user,command").readlines():
        parts = line.split()
        if len(parts) >= 3 and \
               (parts[2].endswith("/apache2") or \
                parts[2].endswith("/httpd") or \
                parts[2].endswith("/httpd2-prefork") or \
                parts[2].endswith("/httpd2-worker")
                ) and \
                parts[1] != 'root':
            wwwuser = parts[1]
            apache_pid = int(parts[0])
            break
    if not wwwuser:
        raise Exception("Cannot find Apache process. Is it running?")

    def scan_apacheconf(apache_conffile):
        confdirs = []
        if apache_conffile[0] != '/':
            apache_conffile = httpd_root + "/" + apache_conffile
        confdirs = []
        for line in file(apache_conffile):
            parts = line.strip().split()
            if len(parts) == 2 and parts[0].lower() == "include":
                if parts[1].endswith("/") or parts[1].endswith("/*.conf"):
                    confdir = "/".join(parts[1].split("/")[:-1])
                    if confdir[0] != "/":
                        confdir = httpd_root + "/" + confdir
                    if not os.path.exists(confdir):
                        continue
                    confdirs.append(confdir) # put at front of list
                else:
                    try:
                        confdirs += scan_apacheconf(parts[1]) # recursive scan
                    except:
                        pass
        return confdirs


    # Find binary
    try:
        nagios_htpasswd_file = None
        nagios_auth_name = None
        apache_binary = process_executable(apache_pid)
        apache_conffile = None
        apache_confdir = None
        httpd_root = ""
        for line in os.popen("%s -V 2>&1" % apache_binary):
            parts = line.split()
            if parts[0] == "-D" and len(parts) > 1:
                p = parts[1].split("=")
                if len(p) == 2 and p[0] == "SERVER_CONFIG_FILE":
                    apache_conffile = p[1].replace('"', "")
                elif len(p) == 2 and p[0] == "HTTPD_ROOT":
                    httpd_root = p[1].replace('"', "")
        if apache_conffile:
            confdirs = scan_apacheconf(apache_conffile)

            if len(confdirs) > 0:
                apache_confdir = confdirs[0]

            for dir in confdirs:
                if dir.endswith("/conf.d"):
                    apache_confdir = dir

            # Search for Nagios configuration. We are interested
            # in the authentication configuration. Most Nagios
            # installations use HTTP basic auth with a htpasswd
            # user file. We want to use that user file for the
            # check_mk web pages.

            def remove_quotes(text):
                try:
                    if text[0] in '"\'':
                        text = text[1:]
                    if text[-1] in '"\'':
                        text = text[:-1]
                except:
                    pass
                return text


            auth_files = []
            auth_names = []
            try:
                for confdir in confdirs:
                    for fn in os.listdir(confdir):
                        file_good = False
                        conffile = file(confdir + "/" + fn)
                        try:
                            new_auth_names = []
                            new_auth_files = []
                            for line in conffile:
                                if nagios_htdocs_dir in line:
                                    file_good = True
                                parts = line.split()
                                if len(parts) == 2 and parts[0].lower() == "authuserfile":
                                    path = remove_quotes(parts[1])
                                    if os.path.exists(path):
                                        new_auth_files.append(path)
                                if len(parts) > 1 and parts[0].lower() == "authname":
                                    parts = line.split(None, 1)
                                    new_auth_names.append(remove_quotes(parts[1].strip()))
                                try:
                                    if len(parts) > 1 and parts[0].lower().startswith("<directory") and "pnp4nagios" in line:
                                        cleanedup = line.replace("<", "").replace(">", "").replace('"', "")
                                        cleanedup = cleanedup[9:]
                                        dir = cleanedup.strip()
                                        if os.path.exists(dir) and os.path.exists(dir + "/application/config/config.php"):
                                            result['pnphtdocsdir'] = dir
                                            result['pnptemplates'] = dir + "/templates"
                                except Exception,e :
                                    pass
                            if file_good:
                                auth_names += new_auth_names
                                auth_files += new_auth_files

                        except Exception, e:
                            pass
                    if len(auth_files) > 0:
                        nagios_htpasswd_file = auth_files[0]
                    if len(auth_names) > 0:
                        nagios_auth_name = auth_names[0]
            except:
                if opt_debug:
                    raise
                pass


    except:
        if opt_debug:
            raise
        apache_confdir = None
        nagios_htpasswd_file = None

    www_groups    = os.popen("id -nG " + wwwuser).read().split()
    nagios_groups = os.popen("id -nG " + nagiosuser).read().split()
    common_groups = [ g for g in www_groups if g in nagios_groups ]
    if len(common_groups) > 1:
        if 'nagios' in common_groups:
            common_group = 'nagios'
        elif 'icinga' in common_groups:
            common_group = 'icinga'
        else:
            common_group = common_groups[0]
    elif len(common_groups) == 1:
        common_group = common_groups[0]
    else:
        common_group = None

    return wwwuser, common_group, apache_confdir, nagios_htpasswd_file, nagios_auth_name


def process_environment(pid):
    # Umgebung des Prozesses bestimmen. Ich brauch das nicht,
    # aber der folgende Code ist einfach cool, oder?
    try:
        env = {}
        for line in file("/proc/%d/environ" % pid).read().split("\0"):
            if '=' in line:
                var, value = entry.split('=', 1)
                env[var] = value
        return env
    except:
        raise Sorry("Cannot get environment of process %d. Aren't you root?" %
                    pid)

def process_executable(pid):
    try:
        return os.readlink("/proc/%d/exe" % pid).split(" ", 1)[0]
    except:
        raise Sorry("Cannot get executable of process %d. Aren't you root?" %
                    pid)

def open_files(pid):
    try:
        # Liste der offenen Dateien. Das ist schon nuetzlicher,
        # denn hier sieht man z.B. die Commandpipe
        procpath = "/proc/%d/fd" % pid
        return [ os.readlink(procpath + "/" + entry) for entry in os.listdir(procpath) ]
    except:
        raise Sorry("Cannot get open files of process %d. Aren't you root?" %
                    pid)

def find_pipes(filenames):
    pipes = []
    for f in filenames:
        try:
            mode = os.stat(f)[stat.ST_MODE]
            if stat.S_ISFIFO(mode):
                pipes.append(f)
        except:
            pass
    return pipes

def parse_nagios_config(configfile):
    conf = []
    for line in file(configfile):
        line = line.strip()
        if line == "" or line[0] == '#':
            continue
        try:
            key, value = line.split('=', 1)
            conf.append((key, value))
        except:
            pass # ignore invalid line (as Nagios seems to do)
    return conf


def detect_pnp():
    global result
    # Jetzt will ich noch das Verzeichnis fuer die Schablonen
    # von PNP finden. Ich erkenne es daran, dass es ein Verzeichnis
    # ist, in dem 'templates' und 'templates.dist' liegen. Dieses
    # Verzeichnis liegt hoffentlich innerhalb der Webseite von
    # Nagios selbst. Dieser Pfad ist in cgi.cfg festgelegt. Das ganze
    # klappt nur bei PNP 0.4
    if 'pnptemplates' not in result:
        try:
            found = []
            def func(arg, dirname, names):
                if 'templates' in names and 'templates.dist' in names:
                    found.append(dirname + "/templates")
            os.path.walk(cgiconf['physical_html_path'], func, None)
            result['pnptemplates'] = found[0]
            if 'pnphtdocsdir' not in result:
                result['pnphtdocsdir'] = result['pnptemplates'].rsplit('/', 1)[0]
        except:
            pass

    # Suche die Konfigurationsdatei von PNP4Nagios. Denn ich will
    # den Eintrag finden, der auf die RRDs zeigt. Den braucht
    # check_mk für das direkte Eintragen in die RRD-Datenbanken
    try:
        pnppath = os.path.dirname(result['pnptemplates'])
        index_php = pnppath + "/index.php"
        for line in file(index_php):
            line = line.strip()
            #  $config = "/usr/local/nagios/etc/pnp/config";
            if line.startswith('$config =') and line.endswith('";'):
                pnpconffile = line.split('"')[1] + ".php"
                result['pnpconffile'] = pnpconffile
                result['pnpconfdir'] = pnpconffile.rsplit("/", 1)[0]
                break
    except:
        pass

    try:
        # For PNP 0.6
        if 'pnpconffile' not in result:
            kohanaconf = result['pnphtdocsdir'] + "/application/config/config.php"
            if os.path.exists(kohanaconf):
                for line in file(kohanaconf):
                    line = line.strip()
                    if not line.startswith("#") and "pnp_etc_path" in line:
                        last = line.split('=')[-1].strip()
                        dir = last.replace("'", "").replace(";", "").replace('"', "")
                        if os.path.exists(dir):
                            result['pnpconfdir'] = dir
                            result['pnpconffile'] = dir + "/config.php"

    except:
        pass

    try:
        for line in file(result['pnpconffile']):
            line = line.strip()
            if line.startswith("$conf['rrdbase']") and line.endswith('";'):
                rrddir = line.split('"')[1]
                if rrddir.endswith('/'):
                    rrddir = rrddir[:-1]
                result['rrddir'] = rrddir
            elif (line.startswith("$conf['base_url']")
                    or line.startswith("$conf['pnp_base']")) \
                  and line.endswith(";"):
                pnp_url = line.split('"')[1]
                if not pnp_url.endswith("/"):
                    pnp_url += "/"
                result["pnp_url"] = pnp_url
    except:
        pass


def detect_omd():
    site = os.getenv("OMD_SITE")
    root = os.getenv("OMD_ROOT")
    if not site or not root:
        return None
    else:
        return {
      'apache_config_dir'       : root + "/etc/apache/conf.d",
      'cgiurl'                  : "/" + site + "/nagios/cgi-bin/",
      'check_icmp_path'         : root + "/lib/nagios/plugins/check_icmp",
      'htdocsdir'               : root + "/share/nagios/htdocs",
      'htpasswd_file'           : root + "/etc/htpasswd",
      'livestatus_in_nagioscfg' : False,
      'nagconfdir'              : root + "/etc/nagios/conf.d",
      'nagiosaddconf'           : "",
      'nagios_auth_name'        : "OMD Monitoring Site " + site,
      'nagios_binary'           : root + "/bin/nagios",
      'nagios_config_file'      : root + "/tmp/nagios/nagios.cfg",
      'nagios_startscript'      : root + "/etc/init.d/nagios",
      'nagios_status_file'      : root + "/var/nagios/status.dat",
      'nagiosurl'               : "/" + site + "/nagios/",
      'nagiosuser'              : site,
      'nagpipe'                 : root + "/tmp/run/nagios.cmd",
      'check_result_path'       : root + "/tmp/nagios/checkresults",
      'pnp_url'                 : "/" + site + "/pnp4nagios/",
      'pnpconffile'             : root + "/etc/pnp4nagios/config.php",
      'pnphtdocsdir'            : root + "/share/pnp4nagios/htdocs",
      'pnptemplates'            : root + "/local/share/check_mk/pnp-templates",
      'rrddir'                  : root + "/var/pnp4nagios/perfdata",
      'wwwgroup'                : site,
      'wwwuser'                 : site,
    }


#                    _
#    _ __ ___   __ _(_)_ __
#   | '_ ` _ \ / _` | | '_ \
#   | | | | | | (_| | | | | |
#   |_| |_| |_|\__,_|_|_| |_|
#

try:
    result = detect_omd()
    if not result:
        result = {}

        pid, nagiosuser, configfile = find_pid_and_configfile()
        nagios_dir = os.path.dirname(configfile)
        result['nagios_config_file'] = configfile
        result['nagiosuser'] = nagiosuser
        pipes = find_pipes(open_files(pid))
        if len(pipes) > 0:
            result['nagpipe'] = pipes[0]

        # Path to executable
        result['nagios_binary'] = process_executable(pid)

        # Nagios version
        result['nagios_version'] = ""
        for line in os.popen(result["nagios_binary"]+ " --version 2>/dev/null"):
            if line.startswith("Nagios Core") or line.startswith("Icinga Core"):
                result['nagios_version'] = line.split()[2]

        # Path to startscript
        for path in [ '/etc/init.d/nagios', '/etc/init.d/nagios3', '/etc/init.d/icinga' ]:
            if os.path.exists(path):
                result['nagios_startscript'] = path
                break

        nagconf = parse_nagios_config(configfile)
        nagconf_dict = dict(nagconf)
        if "check_result_path" in nagconf_dict:
            result['check_result_path'] = nagconf_dict['check_result_path']

        try:
            cgifile = os.path.dirname(configfile) + "/cgi.cfg"
            cgiconf = dict(parse_nagios_config(cgifile))
            result['htdocsdir'] = cgiconf['physical_html_path']
        except:
            cgiconf = {}

        # Suche nach cfg_dir Direktiven. Wir suchen
        # einen flauschigen Platz fuer unsere Konfigdateien
        cfg_dirs = [ value for key, value in nagconf if key == 'cfg_dir' ]
        if len(cfg_dirs) > 0:
            # Wenn es mehrere gibt, bevorzuge ich das, das im gleichen
            # Verzeichnis, wie die Nagios-Konfigdatei selbst liegt.
            # Debian legt ein cfg_dir fuer die Plugins an....
            if len(cfg_dirs) == 1:
                result['nagconfdir'] = cfg_dirs[0]
            else:
                dir = os.path.dirname(configfile)
                for d in cfg_dirs:
                    if os.path.dirname(d) == dir:
                        result['nagconfdir'] = d
                        break
                else:
                    result['nagconfdir'] = cfg_dirs[0]
        else:
            # Mist. Kein cfg_dir in nagios.cfg. Das ist z.B. bei
            # der immer noch verbreiteten Defaultkonfig der Fall.
            # Wir legen einfach selbst eins fest und hängen das
            # eigenmächtig hinten an die Config an
            nagconfdir = nagios_dir + "/check_mk.d"
            result['nagconfdir'] = nagconfdir
            result['nagiosaddconf'] = "cfg_dir=" + nagconfdir

        # Find path to status.dat, the Nagios status file. We
        # need that for the check_mk web pages. Normally the
        # path is configured in nagios.cfg. If no - we still
        # have a chance by parsing the output of nagios3stats.
        nagios_status_file = nagconf_dict.get("status_file")
        if not nagios_status_file:
            for stats_name in [ "stats", "tats" ]:
                try:
                    stats_bin = result['nagios_binary'] + stats_name
                    for line in os.popen(stats_bin + " 2>/dev/null"):
                        if line.startswith("Status File:"):
                            parts = line.split()
                            nagios_status_file = parts[-1]
                            break
                        elif line.startswith("Error reading status file"):
                            parts = line.split()
                            nagios_status_file = parts[-1][1:-1]
                            break
                except:
                    pass

        if nagios_status_file:
            result['nagios_status_file'] = nagios_status_file


        # Ermittle $USER1$ Variablen, da sie in den Plugin-Pfaden
        # auftauchen koennen.
        uservars = {}
        try:
            for line in file(nagconf_dict['resource_file']):
                line = line.strip()
                if line.startswith('$') and '=' in line:
                    varname, value = line.split('=', 1)
                    uservars[varname.strip()] = value.strip()
        except:
            pass


        # Suche nach einem Eintrag zum Laden des livestatus
        # Moduls. Er darf auch auskommentiert sein. Dann lassen
        # wir den Benutzer damit in Ruhe
        found = False
        for line in file(configfile):
            if "broker_module=" in line and "/livestatus.o" in line:
                found = True
                break
        result['livestatus_in_nagioscfg'] = found

        # Jetzt wird's schwieriger: Ich suche nach check_icmp.
        # Ich will keinen find machen, da das erstens ewig
        # dauern kann und zweitens eventl. eine falsche Stelle
        # findet, z.B. innerhalb eines ausgepackten und kompilierten
        # Quellcodes der nagios-plugins. Daher suche ich in
        # allen Objektdateien von Nagios nach command_line.
        # Damit ermittle ich alle Verzeichnisse, in denen Plugins
        # liegen. Dort suche ich dann nach check_icmp. Zur Sicherheit
        # suche ich aber auch unter '/usr/lib/nagios' und '/usr/local/nagios/libexec'
        # und '/usr/local/nagios/plugins'
        found = []
        for dir in cfg_dirs:
            os.path.walk(dir, lambda x,dirname,names: found.append((dirname, names)), None)
        plugin_paths = []
        for dirname, names in found:
            for name in names:
                if name.endswith(".cfg"):
                    path = dirname + "/" + name
                    try:
                        for line in file(path):
                            if line.strip() == '':
                                continue
                            parts = line.strip().split()
                            if parts[0] == "command_line":
                                path = parts[1]
                                for var, value in uservars.items():
                                    path = path.replace(var, value)
                                if path.startswith('/') and path not in plugin_paths:
                                    plugin_paths.append(path)
                    except:
                        pass

        for dir in plugin_paths + \
            [ '/usr/lib/nagios/plugins',
              '/usr/lib64/nagios/plugins',
              '/usr/local/nagios/libexec',
              '/usr/local/nagios/plugins' ]:
            try:
                mode = os.stat(dir)[stat.ST_MODE]
                if not stat.S_ISDIR(mode):
                    dir = os.path.dirname(dir)
                filenames = os.listdir(dir)

                for filename in filenames:
                    if filename == 'check_icmp':
                        result['check_icmp_path'] = dir + '/' + filename
                        break
            except:
                pass


        # Die Basis-Url fuer Nagios ist leider auch nicht immer
        # gleich
        try:
            result['nagiosurl'] = cgiconf['url_html_path']
            result['cgiurl'] = result['nagiosurl'] + "/cgi-bin"
        except:
            pass

        # Suche eine Gruppe, die Nagios mit dem Apache gemeinsam
        # hat. Diese brauchen wir z.B. für logwatch
        try:
            wwwuser, wwwgroup, apache_confdir, nagios_htpasswd_file, nagios_auth_name = \
                     find_apache_properties(nagiosuser, result['htdocsdir'])
            if wwwuser:
                result['wwwuser']  = wwwuser
            if wwwgroup:
                result['wwwgroup'] = wwwgroup
            if apache_confdir:
                result['apache_config_dir'] = apache_confdir
            if nagios_htpasswd_file:
                result['htpasswd_file'] = nagios_htpasswd_file
            if nagios_auth_name:
                result['nagios_auth_name'] = nagios_auth_name
        except Exception, e:
            sys.stderr.write("\033[1;41;35m Cannot determine Apache properties. \033[0m\n"
                             "Reason: %s\n" % e)


        detect_pnp()

    print "# Result of autodetection"
    for var, value in result.items():
        print
        descr = target_values.get(var)
        if descr:
            print "# %s" % descr
        else:
            print "# (unknown value)"
        print "%s='%s'" % (var, value)

    for var, descr in target_values.items():
        if var not in result:
            print
            print "# %s" % descr
            print "# NOT DETECTED: %s" % var

except Sorry, e:
    sys.stderr.write("\033[1;41;35m Sorry: %s \033[0m\n" % e.reason)
    sys.exit(1)

except Exception, e:
    if opt_debug:
        raise
    else:
        sys.stderr.write("* Sorry, something unexpected happened: %s\n\n" % e)
        import traceback
        traceback.print_exc()
        sys.exit(1)
