

backup_domains = {}

if not defaults.omd_root:
    backup_domains.update( {
    "noomd-config": {
      "group"       : _("Configuration"),
      "title"       : _("WATO Configuration"),
      "prefix"      : defaults.default_config_dir,
      "paths"       : [
                        ("dir",  "conf.d/wato"),
                        ("dir",  "multisite.d/wato"),
                        ("file", "multisite.d/sites.mk")
                      ],
      "default"     : True,
    },
    "noomd-personalsettings": {
          "title"       : _("Personal User Settings and Custom Views"),
          "prefix"      :  defaults.var_dir,
          "paths"       : [ ("dir", "web") ],
          "default"     : True
    },
    "noomd-authorization": {
      "group"       : _("Configuration"),
      "title"       : _("Local Authentication Data"),
      "prefix"      : os.path.dirname(defaults.htpasswd_file),
      "paths"       : [
                        ("file", "htpasswd"),
                        ("file", "auth.secret"),
                        ("file", "auth.serials")
                      ],
      "default"     : True
    }})
else:
    backup_domains.update({
        "check_mk": {
          "group"       : _("Configuration"),
          "title"       : _("Hosts, Services, Groups, Timeperiods, Business Intelligence and Monitoring Configuration"),
          "prefix"      : defaults.default_config_dir,
          "paths"       : [
                            ("file", "liveproxyd.mk"),
                            ("file", "main.mk"),
                            ("file", "final.mk"),
                            ("file", "local.mk"),
                            ("file", "mkeventd.mk"),

                            ("dir", "conf.d"),
                            ("dir", "multisite.d"),
                            ("dir", "mkeventd.d"),
                            ("dir", "mknotifyd.d"),
                          ],
          "default"     : True,
        },
        "authorization": {
          "group"       : _("Configuration"),
          "title"       : _("Local Authentication Data"),
          "prefix"      : os.path.dirname(defaults.htpasswd_file),
          "paths"       : [
                            ("file", "htpasswd"),
                            ("file", "auth.secret"),
                            ("file", "auth.serials")
                          ],
          "default"     : True
        },
        "personalsettings": {
          "title"       : _("Personal User Settings and Custom Views"),
          "prefix"      :  defaults.var_dir,
          "paths"       : [ ("dir", "web") ],
          "default"     : True
        },
        "autochecks": {
          "group"       : _("Configuration"),
          "title"       : _("Automatically Detected Services"),
          "prefix"      : defaults.autochecksdir,
          "paths"       : [ ("dir", "") ],
        },
        "snmpwalks": {
          "title"       : _("Stored SNMP Walks"),
          "prefix"      : defaults.snmpwalks_dir,
          "paths"       : [ ("dir", "") ],
        },
        "logwatch": {
          "group"       : _("Historic Data"),
          "title"       : _("Logwatch Data"),
          "prefix"      : defaults.var_dir,
          "paths"       : [
                            ("dir",  "logwatch"),
                          ],
        },
        "corehistory": {
          "group"       : _("Historic Data"),
          "title"       : _("Monitoring History"),
          "prefix"      : defaults.omd_root,
          "paths"       : [
                            ("dir",  "var/nagios/archive"),
                            ("file", "var/nagios/nagios.log"),
                            ("dir",  "var/icinga/archive"),
                            ("file", "var/icinga/icinga.log"),
                            ("dir",  "var/check_mk/core/archive"),
                            ("file", "var/check_mk/core/history"),
                          ],
        },
        "performancedata": {
          "group"       : _("Historic Data"),
          "title"       : _("Performance Data"),
          "prefix"      : defaults.omd_root,
          "paths"       : [
                            ("dir",  "var/pnp4nagios/perfdata"),
                            ("dir",  "var/rrdcached"),
                          ],
        },
        "applicationlogs": {
          "group"       : _("Historic Data"),
          "title"       : _("Application Logs"),
          "prefix"      : defaults.omd_root,
          "paths"       : [
                            ("dir",  "var/log"),
                            ("file", "var/check_mk/notify/notify.log"),
                            ("file", "var/nagios/livestatus.log"),
                            ("dir",  "var/pnp4nagios/log"),
                          ],
        },
        "mkeventstatus": {
          "group"       : _("Configuration"),
          "title"       : _("Event Console Configuration"),
          "prefix"      : defaults.omd_root,
          "paths"       : [
                            ("dir",  "etc/check_mk/mkeventd.d"),
                          ],
          "default"     : True
        },
        "mkeventhistory": {
          "group"       : _("Historic Data"),
          "title"       : _("Event Console Archive and Current State"),
          "prefix"      : defaults.omd_root,
          "paths"       : [
                            ("dir",  "var/mkeventd/history"),
                            ("file", "var/mkeventd/status"),
                          ],
        },
        "dokuwiki": {
          "title"       : _("Doku Wiki Pages and Settings"),
          "prefix"      : defaults.omd_root,
          "paths"       : [
                            ("dir",  "var/dokuwiki"),
                          ],
        },
        "nagvis": {
          "title"       : _("NagVis Maps, Configurations and User Files"),
          "prefix"      : defaults.omd_root,
          "paths"       : [
                            ("dir",  "local/share/nagvis"),
                            ("dir",  "etc/nagvis"),
                            ("dir",  "var/nagvis"),
                          ],
        },
    })
