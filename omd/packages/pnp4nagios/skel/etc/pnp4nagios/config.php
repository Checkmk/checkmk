<?php
##
## Program: pnp4nagios, Performance Data Addon for Nagios(r)
## License: GPL
## Copyright (c) 2005-2010 Joerg Linge (http://www.pnp4nagios.org)
##
## This program is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License
## as published by the Free Software Foundation; either version 2
## of the License, or (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
##
# Credit:  Tobi Oetiker, http://people.ee.ethz.ch/~oetiker/webtools/rrdtool/
#

# URL rewriting is used by default to create friendly URLs. 
# Set this value to '0' if URL rewriting is not available on your system.
#
$conf['use_url_rewriting'] = 1;
#
# Location of rrdtool binary
#
$conf['rrdtool'] = "###ROOT###/bin/rrdtool";
#
# RRDTool image size of graphs
#
$conf['graph_width'] = "500";
$conf['graph_height'] = "100";
#
# RRDTool image size of graphs in zoom window
#
$conf['zgraph_width'] = "500";
$conf['zgraph_height'] = "100";
#
# Right zoom box offset.
# rrdtool 1.3.x = 30px 
# rrdtool 1.4.x = 22px
#
$conf['right_zoom_offset'] = 22;
#
# RRDTool image size of PDFs
#
$conf['pdf_width'] = "675";
$conf['pdf_height'] = "100";
#
# Additional options for RRDTool
#
# Example: White background and no border
# "--watermark 'Copyright by example.com' --slope-mode --color BACK#FFF --color SHADEA#FFF --color SHADEB#FFF"
#
$conf['graph_opt'] = "--slope-mode --color BACK#FFF --color SHADEA#FFF --color SHADEB#FFF"; 
#
# Additional options for RRDTool used while creating PDFs
#
$conf['pdf_graph_opt'] = ""; 
#
# Directory where the RRD Files will be stored
#
$conf['rrdbase'] = "###ROOT###/var/pnp4nagios/perfdata/";
#
# Location of "page" configs
#
$conf['page_dir'] = "###ROOT###/etc/pnp4nagios/pages/";
#
# Site refresh time in seconds
#
$conf['refresh'] = "90";
#
# Max age for RRD files in seconds
# 
$conf['max_age'] = 60*60*6;   
#
# Directory for temporary files used for PDF creation 
#
$conf['temp'] = "###ROOT###/tmp";
#
# Link back to Nagios or Thruk ( www.thruk.org ) 
#
$conf['nagios_base'] = "/###SITE###/nagios/cgi-bin";

#
# Link back to check_mk´s multisite ( http://mathias-kettner.de/checkmk_multisite.html )
#
$conf['multisite_base_url'] = "/###SITE###/check_mk";
#
# Multisite Site ID this PNP installation is linked to
# This is the same value as defined in etc/multisite.mk
#
$conf['multisite_site'] = "###SITE###";

#
# check authorization against mk_livestatus API 
# Available since 0.6.10
#
$conf['auth_enabled'] = TRUE;

#
# Using the multisite cookie based authentication when no
# REMOTE_USER available.
#
$conf['auth_multisite_enabled']  = TRUE;
$conf['auth_multisite_htpasswd'] = '###ROOT###/etc/htpasswd';
$conf['auth_multisite_secret']   = '###ROOT###/etc/auth.secret';

#
# Livestatus socket path
# 
$conf['livestatus_socket'] = "unix:###ROOT###/tmp/run/live";

#
# Which user is allowed to see all services or all hosts?
# Keywords: <USERNAME>
# Example: conf['allowed_for_all_services'] = "nagiosadmin,operator";
# This option is used while $conf['auth_enabled'] = TRUE
$conf['allowed_for_all_services'] = "omdadmin,cmkadmin";
$conf['allowed_for_all_hosts'] = "omdadmin,cmkadmin";

# Which user is allowed to see additional service links ?
# Keywords: EVERYONE NONE <USERNAME>
# Example: conf['allowed_for_service_links'] = "nagiosadmin,operator";
# 
$conf['allowed_for_service_links'] = "EVERYONE";
#
# Who can use the host search function ?
# Keywords: EVERYONE NONE <USERNAME>
#
$conf['allowed_for_host_search'] = "EVERYONE";
#
# Who can use the host overview ?
# This function is called if no Service Description is given.  
#
$conf['allowed_for_host_overview'] = "EVERYONE";
#
# Who can use the Pages function?
# Keywords: EVERYONE NONE <USERNAME>
# Example: conf['allowed_for_pages'] = "nagiosadmin,operator";
#
$conf['allowed_for_pages'] = "EVERYONE";

#
# Which timerange should be used for the host overview site ? 
# use a key from array $views[]
#
$conf['overview-range'] = 1 ;
#
# Scale the preview images used in /popup 
#
$conf['popup-width'] = "300px";
#
# jQuery UI Theme
# http://jqueryui.com/themeroller/
# Possible values are: lightness, smoothness, redmond, multisite
$conf['ui-theme'] = 'multisite';

# Language definitions to use.
# valid options are en_US, de_DE, es_ES, ru_RU, fr_FR 
#
$conf['lang'] = "en_US";
#
# Date format
#
$conf['date_fmt'] = "d.m.y G:i";
#
# This option breaks down the template name based on _ and then starts to 
# build it up and check the different template directories for a suitable template.
#
# Example:
#
# Template to be used: check_esx3_host_net_usage you create a check_esx3.php
#
# It will find and match on check_esx3 first in templates dir then in templates.dist
#
$conf['enable_recursive_template_search'] = 1;
#
# Direct link to the raw XML file.
#
$conf['show_xml_icon'] = 1;
#
# Use FPDF Lib for PDF creation ?
#
$conf['use_fpdf'] = 1;	
#
# Use this file as PDF background.
#
$conf['background_pdf'] = '###ROOT###/etc/pnp4nagios/background.pdf' ;
#
# Enable Calendar
#
$conf['use_calendar'] = 1;
#
# Define default views with title and start timerange in seconds 
#
# remarks: required escape on " with backslash
#
#$views[] = array('title' => 'One Hour',  'start' => (60*60) );
$views[] = array('title' => '4 Hours',   'start' => (60*60*4) );
$views[] = array('title' => '25 Hours',  'start' => (60*60*25) );
$views[] = array('title' => 'One Week',  'start' => (60*60*25*7) );
$views[] = array('title' => 'One Month', 'start' => (60*60*24*32) );
$views[] = array('title' => 'One Year',  'start' => (60*60*24*380) );

#
# rrdcached support
# Use only with rrdtool svn revision 1511+
#
# $conf['RRD_DAEMON_OPTS'] = 'unix:/tmp/rrdcached.sock';
$conf['RRD_DAEMON_OPTS'] = 'unix:###ROOT###/tmp/run/rrdcached.sock';

# A list of directories to search for templates
# /omd/versions/0.42/share/pnp4nagios/htdocs/templates.dist is always the last directory to be searched for templates
#
# Add your own template directories here
# First match wins!
$conf['template_dirs'][] = '###ROOT###/etc/pnp4nagios/templates';
$conf['template_dirs'][] = '###ROOT###/local/share/check_mk/pnp-templates'; 
$conf['template_dirs'][] = '###ROOT###/share/check_mk/pnp-templates';
$conf['template_dirs'][] = '###ROOT###/share/pnp4nagios/htdocs/templates';
$conf['template_dirs'][] = '###ROOT###/share/pnp4nagios/htdocs/templates.dist';

#
# Directory to search for special templates
#
$conf['special_template_dir'] = '###ROOT###/etc/pnp4nagios/templates.special';

#
# Regex to detect mobile devices
# This regex is evaluated against the USER_AGENT String
#
$conf['mobile_devices'] = 'iPhone|iPod|iPad|android';

#
# additional colour schemes
# values taken from www.colorbrewer2.org
# for details on usage refer to the documentation of the helper functions 
#
$scheme['Reds']     = array ('#FEE0D2','#FCBBA1','#FC9272','#FB6A4A','#EF3B2C','#CB181D','#A50F15','#67000D');
$scheme['Greens']   = array ('#E5F5E0','#C7E9C0','#A1D99B','#74C476','#41AB5D','#23AB45','#006D2C','#00441B');
$scheme['Blues']    = array ('#DEEBF7','#C6DBEF','#9ECAE1','#6BAED6','#4292C6','#2171B5','#08519C','#08306B');
$scheme['Oranges']  = array ('#FEE6CE','#FDD0A2','#FDAE6B','#FD8D3C','#F16913','#D94801','#A63603','#7F2704');
$scheme['Purples']  = array ('#EFEDF5','#DADAEB','#BDBDDC','#9E9AC8','#807DBA','#6A51A3','#54278F','#3F007A');
$scheme['RdPu']     = array ('#FDE0DD','#FCC5C0','#FA9FB5','#F768A1','#DD3497','#AE017E','#7A0177','#49006A');
$scheme['Dark2']    = array ('#1B9E77','#D95F02','#7570B3','#E7298A','#66A61E','#E6ab02','#a6761d','#666666');
$scheme['BrBG']     = array ('#543005','#8C510A','#BF812D','#DFC27D','#F6E8C3','#C7EAE5','#80CDC1','#35978F','#01665E','#003C30');
$scheme['PiYG']     = array ('#8E0152','#C51B7D','#DE77AE','#F1B6DA','#FDE0EF','#E6F5D0','#B8E186','#7FBC41','#4D9221','#276419');
$scheme['PRGn']     = array ('#40004B','#762A83','#9970AB','#C2A5CF','#E7D4E8','#D9F0D3','#A6DBA0','#5AAE61','#1B7837','#00441B');
$scheme['PuOr']     = array ('#7F3B08','#B35806','#E08214','#FDB863','#FEE0B6','#D8DAEB','#B2ABD2','#8073AC','#542788','#2D004B');
$scheme['RdBu']     = array ('#67001F','#B2182B','#D6604D','#F4A582','#FDDBC7','#D1E5F0','#92C5DE','#4393C3','#2166AC','#053061');
$scheme['RdGy']     = array ('#67001F','#B2182B','#D6604D','#F4A582','#FDDBC7','#E0E0E0','#BABABA','#878787','#4D4D4D','#1A1A1A');
$scheme['RdYlBu']   = array ('#A50026','#D73027','#F46D43','#FDAE61','#FEE090','#E0F3F8','#ABD9E9','#74ADD1','#4575B4','#313695');
$scheme['RdYlGn']   = array ('#A50026','#D73027','#F46D43','#FDAE61','#FEE08B','#D9EF8B','#A6D96A','#66BD63','#1A9850','#006837');
$scheme['Spectral'] = array ('#9E0142','#D53E4F','#F46D43','#FDAE61','#FEE08B','#E6F598','#ABDDA4','#66C2A5','#3288BD','#5E4FA2');
$scheme['Paired']   = array ('#A6CEE3','#1F78B4','#B2DF8A','#33A02C','#FB9A99','#E31A1C','#FDBF6F','#FF7F00','#CAB2D6','#6A3D9A');
$scheme['mixed1']   = array ('#8C510A','#2166ac','#BF812D','#4393c3','#DFC27D','#92c5de','#F6E8C3','#d1e5f0',
                             '#fddbc7','#C7EAE5','#f4a582','#80CDC1','#d6604d','#35978F','#b2182b','#01665E');
$scheme['mixed2']   = array ('#b2182b','#2166ac','#d6604d','#4393c3','#f4a582','#92c5de','#fddbc7','#d1e5f0',
                             '#F6E8C3','#C7EAE5','#DFC27D','#80CDC1','#BF812D','#35978F','#8C510A','#01665E');
$scheme['mixed3']   = array ('#67001F','#80CDC1','#B2182B','#35978F','#D6604D','#01665E','#F4A582','#003C30',
                             '#FDDBC7','#92C5DE','#D1E5F0','#2166AC','#4393C3','#8C510A','#053061','#BF812D');

?>
