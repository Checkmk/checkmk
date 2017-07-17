; <?php return 1; ?>
; -----------------------------------------------------------------
; Don't touch this file. It is under control of OMD. Modifying this
; file might break the update mechanism of OMD.
;
; If you want to customize your NagVis configuration please use the
; etc/nagvis/nagvis.ini.php file.
; -----------------------------------------------------------------

[global]
sesscookiepath="/###SITE###/nagvis"
authorisation_group_perms_file="###ROOT###/etc/nagvis/perms.db"

[paths]
base="###ROOT###/share/nagvis/"
local_base="###ROOT###/local/share/nagvis/"
cfg="###ROOT###/etc/nagvis/"
mapcfg="###ROOT###/etc/nagvis/maps/"
geomap="###ROOT###/etc/nagvis/geomap/"
var="###ROOT###/tmp/nagvis/"
sharedvar="###ROOT###/tmp/nagvis/share/"
profiles="###ROOT###/var/nagvis/profiles/"
htmlbase="/###SITE###/nagvis"
local_htmlbase="/###SITE###/nagvis/local"
htmlcgi="/###SITE###/nagios/cgi-bin"

[defaults]
backend="###SITE###"

[backend_###SITE###]
backendtype="mklivestatus"
socket="unix:###ROOT###/tmp/run/live"

[backend_###SITE###_bi]
backendtype="mkbi"
base_url="http://localhost/###SITE###/check_mk/"
auth_user="automation"
auth_secret_file="###ROOT###/var/check_mk/web/automation/automation.secret"
timeout=10
