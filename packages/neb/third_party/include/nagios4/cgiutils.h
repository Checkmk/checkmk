/************************************************************************
 *
 * CGIUTILS.H - Header file for common CGI functions
 *
 * License:
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as
 * published by the Free Software Foundation.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
 ************************************************************************/

#ifndef _CGIUTILS_H
#define _CGIUTILS_H
#include "lib/libnagios.h"
#include "logging.h"
#include "objects.h"
#include "cgiauth.h"

NAGIOS_BEGIN_DECL

	/**************************** CGI REFRESH RATE ******************************/

#define DEFAULT_REFRESH_RATE	60	/* 60 second refresh rate for CGIs */


	/******************************* CGI NAMES **********************************/

#define STATUS_CGI		"status.cgi"
#define STATUSMAP_CGI		"statusmap.cgi"
#define STATUSWORLD_CGI	        "statuswrl.cgi"
#define COMMAND_CGI		"cmd.cgi"
#define EXTINFO_CGI		"extinfo.cgi"
#define SHOWLOG_CGI		"showlog.cgi"
#define NOTIFICATIONS_CGI	"notifications.cgi"
#define HISTORY_CGI		"history.cgi"
#define CONFIG_CGI              "config.cgi"
#define OUTAGES_CGI		"outages.cgi"
#define TRENDS_CGI		"trends.cgi"
#define AVAIL_CGI		"avail.cgi"
#define TAC_CGI			"tac.cgi"
#define STATUSWML_CGI           "statuswml.cgi"
#define TRACEROUTE_CGI		"traceroute.cgi"
#define HISTOGRAM_CGI		"histogram.cgi"
#define CHECKSANITY_CGI	   	"checksanity.cgi"
#define MINISTATUS_CGI          "ministatus.cgi"
#define SUMMARY_CGI	        "summary.cgi"


	/**************************** STYLE SHEET NAMES ******************************/

#define COMMON_CSS		"common.css"

#define SHOWLOG_CSS		"showlog.css"
#define STATUS_CSS		"status.css"
#define STATUSMAP_CSS		"statusmap.css"
#define COMMAND_CSS		"cmd.css"
#define EXTINFO_CSS		"extinfo.css"
#define NOTIFICATIONS_CSS	"notifications.css"
#define HISTORY_CSS		"history.css"
#define CONFIG_CSS		"config.css"
#define OUTAGES_CSS		"outages.css"
#define TRENDS_CSS		"trends.css"
#define AVAIL_CSS		"avail.css"
#define TAC_CSS			"tac.css"
#define HISTOGRAM_CSS		"histogram.css"
#define CHECKSANITY_CSS		"checksanity.css"
#define MINISTATUS_CSS          "ministatus.css"
#define SUMMARY_CSS             "summary.css"

	/********************************* JAVASCRIPT INCLUDES **********************/
#define JQUERY_JS		"jquery-1.7.1.min.js"

	/********************************* ICONS ************************************/

#define STATUS_ICON_WIDTH		20
#define STATUS_ICON_HEIGHT		20

#define INFO_ICON			"info.png"
#define INFO_ICON_ALT			"Informational Message"
#define START_ICON			"start.gif"
#define START_ICON_ALT			"Program Start"
#define STOP_ICON			"stop.gif"
#define STOP_ICON_ALT			"Program End"
#define RESTART_ICON			"restart.gif"
#define RESTART_ICON_ALT		"Program Restart"
#define OK_ICON				"recovery.png"
#define OK_ICON_ALT			"Service Ok"
#define CRITICAL_ICON			"critical.png"
#define CRITICAL_ICON_ALT		"Service Critical"
#define WARNING_ICON			"warning.png"
#define WARNING_ICON_ALT		"Service Warning"
#define UNKNOWN_ICON			"unknown.png"
#define UNKNOWN_ICON_ALT		"Service Unknown"
#define NOTIFICATION_ICON		"notify.gif"
#define NOTIFICATION_ICON_ALT		"Service Notification"
#define LOG_ROTATION_ICON		"logrotate.png"
#define LOG_ROTATION_ICON_ALT		"Log Rotation"
#define EXTERNAL_COMMAND_ICON		"command.png"
#define EXTERNAL_COMMAND_ICON_ALT	"External Command"

#define STATUS_DETAIL_ICON		"status2.gif"
#define STATUS_OVERVIEW_ICON		"status.gif"
#define STATUSMAP_ICON                  "status3.gif"
#define STATUSWORLD_ICON                "status4.gif"
#define EXTINFO_ICON                	"extinfo.gif"
#define HISTORY_ICON			"history.gif"
#define CONTACTGROUP_ICON		"contactgroup.gif"
#define TRENDS_ICON			"trends.gif"

#define DISABLED_ICON			"disabled.gif"
#define ENABLED_ICON			"enabled.gif"
#define PASSIVE_ONLY_ICON		"passiveonly.gif"
#define NOTIFICATIONS_DISABLED_ICON	"ndisabled.gif"
#define ACKNOWLEDGEMENT_ICON            "ack.gif"
#define REMOVE_ACKNOWLEDGEMENT_ICON     "noack.gif"
#define COMMENT_ICON			"comment.gif"
#define DELETE_ICON			"delete.gif"
#define DELAY_ICON			"delay.gif"
#define DOWNTIME_ICON			"downtime.gif"
#define PASSIVE_ICON			"passiveonly.gif"
#define RIGHT_ARROW_ICON		"right.gif"
#define LEFT_ARROW_ICON			"left.gif"
#define UP_ARROW_ICON			"up.gif"
#define DOWN_ARROW_ICON			"down.gif"
#define FLAPPING_ICON			"flapping.gif"
#define SCHEDULED_DOWNTIME_ICON		"downtime.gif"
#define EMPTY_ICON			"empty.gif"

#define ACTIVE_ICON			"active.gif"
#define ACTIVE_ICON_ALT                 "Active Mode"
#define STANDBY_ICON			"standby.gif"
#define STANDBY_ICON_ALT                "Standby Mode"

#define HOST_DOWN_ICON			"critical.png"
#define HOST_DOWN_ICON_ALT		"Host Down"
#define HOST_UNREACHABLE_ICON		"critical.png"
#define HOST_UNREACHABLE_ICON_ALT	"Host Unreachable"
#define HOST_UP_ICON			"recovery.png"
#define HOST_UP_ICON_ALT		"Host Up"
#define HOST_NOTIFICATION_ICON		"notify.gif"
#define HOST_NOTIFICATION_ICON_ALT	"Host Notification"

#define SERVICE_EVENT_ICON		"serviceevent.gif"
#define SERVICE_EVENT_ICON_ALT		"Service Event Handler"
#define HOST_EVENT_ICON			"hostevent.gif"
#define HOST_EVENT_ICON_ALT		"Host Event Handler"

#define THERM_OK_IMAGE			"thermok.png"
#define THERM_WARNING_IMAGE		"thermwarn.png"
#define THERM_CRITICAL_IMAGE		"thermcrit.png"

#define CONFIGURATION_ICON		"config.gif"
#define NOTES_ICON			"notes.gif"
#define ACTION_ICON			"action.gif"
#define DETAIL_ICON                     "detail.gif"

#define PARENT_TRAVERSAL_ICON		"parentup.gif"

#define TAC_DISABLED_ICON		"tacdisabled.png"
#define TAC_ENABLED_ICON		"tacenabled.png"

#define ZOOM1_ICON			"zoom1.gif"
#define ZOOM2_ICON			"zoom2.gif"

#define CONTEXT_HELP_ICON1		"contexthelp1.gif"
#define CONTEXT_HELP_ICON2		"contexthelp2.gif"

#define SPLUNK_SMALL_WHITE_ICON		"splunk1.gif"
#define SPLUNK_SMALL_BLACK_ICON		"splunk2.gif"

#define FIRST_PAGE_ICON			"b_first2.png"
#define LAST_PAGE_ICON			"b_last2.png"
#define NEXT_PAGE_ICON			"b_next2.png"
#define PREVIOUS_PAGE_ICON		"b_prev2.png"


	/********************* EXTENDED INFO CGI DISPLAY TYPES  *********************/

#define DISPLAY_PROCESS_INFO		0
#define DISPLAY_HOST_INFO		1
#define DISPLAY_SERVICE_INFO		2
#define DISPLAY_COMMENTS		3
#define DISPLAY_PERFORMANCE		4
#define DISPLAY_HOSTGROUP_INFO		5
#define DISPLAY_DOWNTIME		6
#define DISPLAY_SCHEDULING_QUEUE	7
#define DISPLAY_SERVICEGROUP_INFO       8


	/************************ COMMAND CGI COMMAND MODES *************************/

#define CMDMODE_NONE            0
#define CMDMODE_REQUEST         1
#define CMDMODE_COMMIT          2



	/******************** HOST AND SERVICE NOTIFICATION TYPES ******************/

#define NOTIFICATION_ALL		0	/* all service and host notifications */
#define NOTIFICATION_SERVICE_ALL	1	/* all types of service notifications */
#define NOTIFICATION_HOST_ALL		2	/* all types of host notifications */
#define NOTIFICATION_SERVICE_WARNING	4
#define NOTIFICATION_SERVICE_UNKNOWN	8
#define NOTIFICATION_SERVICE_CRITICAL	16
#define NOTIFICATION_SERVICE_RECOVERY	32
#define NOTIFICATION_HOST_DOWN		64
#define NOTIFICATION_HOST_UNREACHABLE	128
#define NOTIFICATION_HOST_RECOVERY	256
#define NOTIFICATION_SERVICE_ACK	512
#define NOTIFICATION_HOST_ACK		1024
#define NOTIFICATION_SERVICE_FLAP	2048
#define NOTIFICATION_HOST_FLAP		4096
#define NOTIFICATION_SERVICE_CUSTOM     8192
#define NOTIFICATION_HOST_CUSTOM        16384


	/********************** HOST AND SERVICE ALERT TYPES **********************/

#define HISTORY_ALL			0	/* all service and host alert */
#define HISTORY_SERVICE_ALL		1	/* all types of service alerts */
#define HISTORY_HOST_ALL		2	/* all types of host alerts */
#define HISTORY_SERVICE_WARNING		4
#define HISTORY_SERVICE_UNKNOWN		8
#define HISTORY_SERVICE_CRITICAL	16
#define HISTORY_SERVICE_RECOVERY	32
#define HISTORY_HOST_DOWN		64
#define HISTORY_HOST_UNREACHABLE	128
#define HISTORY_HOST_RECOVERY		256


	/****************************** SORT TYPES  *******************************/

#define SORT_NONE			0
#define SORT_ASCENDING			1
#define SORT_DESCENDING			2


	/***************************** SORT OPTIONS  ******************************/

#define SORT_NOTHING			0
#define SORT_HOSTNAME			1
#define SORT_SERVICENAME		2
#define SORT_SERVICESTATUS		3
#define SORT_LASTCHECKTIME		4
#define SORT_CURRENTATTEMPT		5
#define SORT_STATEDURATION		6
#define SORT_NEXTCHECKTIME		7
#define SORT_HOSTSTATUS                 8
#define SORT_HOSTURGENCY                9


	/****************** HOST AND SERVICE FILTER PROPERTIES  *******************/

#define HOST_SCHEDULED_DOWNTIME		1
#define HOST_NO_SCHEDULED_DOWNTIME	2
#define HOST_STATE_ACKNOWLEDGED		4
#define HOST_STATE_UNACKNOWLEDGED	8
#define HOST_CHECKS_DISABLED		16
#define HOST_CHECKS_ENABLED		32
#define HOST_EVENT_HANDLER_DISABLED	64
#define HOST_EVENT_HANDLER_ENABLED	128
#define HOST_FLAP_DETECTION_DISABLED	256
#define HOST_FLAP_DETECTION_ENABLED	512
#define HOST_IS_FLAPPING		1024
#define HOST_IS_NOT_FLAPPING		2048
#define HOST_NOTIFICATIONS_DISABLED	4096
#define HOST_NOTIFICATIONS_ENABLED	8192
#define HOST_PASSIVE_CHECKS_DISABLED	16384
#define HOST_PASSIVE_CHECKS_ENABLED	32768
#define HOST_PASSIVE_CHECK           	65536
#define HOST_ACTIVE_CHECK            	131072
#define HOST_HARD_STATE			262144
#define HOST_SOFT_STATE			524288


#define SERVICE_SCHEDULED_DOWNTIME	1
#define SERVICE_NO_SCHEDULED_DOWNTIME	2
#define SERVICE_STATE_ACKNOWLEDGED	4
#define SERVICE_STATE_UNACKNOWLEDGED	8
#define SERVICE_CHECKS_DISABLED		16
#define SERVICE_CHECKS_ENABLED		32
#define SERVICE_EVENT_HANDLER_DISABLED	64
#define SERVICE_EVENT_HANDLER_ENABLED	128
#define SERVICE_FLAP_DETECTION_ENABLED	256
#define SERVICE_FLAP_DETECTION_DISABLED	512
#define SERVICE_IS_FLAPPING		1024
#define SERVICE_IS_NOT_FLAPPING		2048
#define SERVICE_NOTIFICATIONS_DISABLED	4096
#define SERVICE_NOTIFICATIONS_ENABLED	8192
#define SERVICE_PASSIVE_CHECKS_DISABLED	16384
#define SERVICE_PASSIVE_CHECKS_ENABLED	32768
#define SERVICE_PASSIVE_CHECK           65536
#define SERVICE_ACTIVE_CHECK            131072
#define SERVICE_HARD_STATE		262144
#define SERVICE_SOFT_STATE		524288


	/****************************** SSI TYPES  ********************************/

#define SSI_HEADER                      0
#define SSI_FOOTER                      1



	/************************ CONTEXT-SENSITIVE HELP  *************************/

#define CONTEXTHELP_STATUS_DETAIL	"A1"
#define CONTEXTHELP_STATUS_HGOVERVIEW	"A2"
#define CONTEXTHELP_STATUS_HGSUMMARY	"A3"
#define CONTEXTHELP_STATUS_HGGRID	"A4"
#define CONTEXTHELP_STATUS_SVCPROBLEMS	"A5"
#define CONTEXTHELP_STATUS_HOST_DETAIL  "A6"
#define CONTEXTHELP_STATUS_HOSTPROBLEMS "A7"
#define CONTEXTHELP_STATUS_SGOVERVIEW   "A8"
#define CONTEXTHELP_STATUS_SGSUMMARY    "A9"
#define CONTEXTHELP_STATUS_SGGRID       "A10"

#define CONTEXTHELP_TAC			"B1"

#define CONTEXTHELP_MAP			"C1"

#define CONTEXTHELP_LOG			"D1"

#define CONTEXTHELP_HISTORY		"E1"

#define CONTEXTHELP_NOTIFICATIONS	"F1"

#define CONTEXTHELP_TRENDS_MENU1	"G1"
#define CONTEXTHELP_TRENDS_MENU2	"G2"
#define CONTEXTHELP_TRENDS_MENU3	"G3"
#define CONTEXTHELP_TRENDS_MENU4	"G4"
#define CONTEXTHELP_TRENDS_HOST		"G5"
#define CONTEXTHELP_TRENDS_SERVICE	"G6"

#define CONTEXTHELP_AVAIL_MENU1		"H1"
#define CONTEXTHELP_AVAIL_MENU2		"H2"
#define CONTEXTHELP_AVAIL_MENU3		"H3"
#define CONTEXTHELP_AVAIL_MENU4		"H4"
#define CONTEXTHELP_AVAIL_MENU5		"H5"
#define CONTEXTHELP_AVAIL_HOSTGROUP	"H6"
#define CONTEXTHELP_AVAIL_HOST		"H7"
#define CONTEXTHELP_AVAIL_SERVICE	"H8"
#define CONTEXTHELP_AVAIL_SERVICEGROUP	"H9"

#define CONTEXTHELP_EXT_HOST		"I1"
#define CONTEXTHELP_EXT_SERVICE		"I2"
#define CONTEXTHELP_EXT_HOSTGROUP	"I3"
#define CONTEXTHELP_EXT_PROCESS		"I4"
#define CONTEXTHELP_EXT_PERFORMANCE	"I5"
#define CONTEXTHELP_EXT_COMMENTS	"I6"
#define CONTEXTHELP_EXT_DOWNTIME	"I7"
#define CONTEXTHELP_EXT_QUEUE		"I8"
#define CONTEXTHELP_EXT_SERVICEGROUP	"I9"

#define CONTEXTHELP_CMD_INPUT		"J1"
#define CONTEXTHELP_CMD_COMMIT		"J2"

#define CONTEXTHELP_OUTAGES		"K1"

#define CONTEXTHELP_CONFIG_MENU			"L1"
#define CONTEXTHELP_CONFIG_HOSTS		"L2"
#define CONTEXTHELP_CONFIG_HOSTDEPENDENCIES	"L3"
#define CONTEXTHELP_CONFIG_HOSTESCALATIONS	"L4"
#define CONTEXTHELP_CONFIG_HOSTGROUPS		"L5"
#define CONTEXTHELP_CONFIG_HOSTGROUPESCALATIONS	"L6"
#define CONTEXTHELP_CONFIG_SERVICES		"L7"
#define CONTEXTHELP_CONFIG_SERVICEDEPENDENCIES	"L8"
#define CONTEXTHELP_CONFIG_SERVICEESCALATIONS	"L9"
#define CONTEXTHELP_CONFIG_CONTACTS		"L10"
#define CONTEXTHELP_CONFIG_CONTACTGROUPS	"L11"
#define CONTEXTHELP_CONFIG_TIMEPERIODS		"L12"
#define CONTEXTHELP_CONFIG_COMMANDS		"L13"
#define CONTEXTHELP_CONFIG_HOSTEXTINFO		"L14"
#define CONTEXTHELP_CONFIG_SERVICEEXTINFO	"L15"
#define CONTEXTHELP_CONFIG_SERVICEGROUPS        "L16"

#define CONTEXTHELP_HISTOGRAM_MENU1	"M1"
#define CONTEXTHELP_HISTOGRAM_MENU2	"M2"
#define CONTEXTHELP_HISTOGRAM_MENU3	"M3"
#define CONTEXTHELP_HISTOGRAM_MENU4	"M4"
#define CONTEXTHELP_HISTOGRAM_HOST	"M5"
#define CONTEXTHELP_HISTOGRAM_SERVICE	"M6"

#define CONTEXTHELP_SUMMARY_MENU                   "N1"
#define CONTEXTHELP_SUMMARY_RECENT_ALERTS          "N2"
#define CONTEXTHELP_SUMMARY_ALERT_TOTALS           "N3"
#define CONTEXTHELP_SUMMARY_HOSTGROUP_ALERT_TOTALS "N4"
#define CONTEXTHELP_SUMMARY_HOST_ALERT_TOTALS      "N5"
#define CONTEXTHELP_SUMMARY_SERVICE_ALERT_TOTALS   "N6"
#define CONTEXTHELP_SUMMARY_ALERT_PRODUCERS        "N7"
#define CONTEXTHELP_SUMMARY_SERVICEGROUP_ALERT_TOTALS "N8"


	/************************** LIFO RETURN CODES  ****************************/

#define LIFO_OK			0
#define LIFO_ERROR_MEMORY	1
#define LIFO_ERROR_FILE		2
#define LIFO_ERROR_DATA		3





/*************************** DATA STRUCTURES  *****************************/

/* LIFO data structure */
typedef struct lifo_struct {
	char *data;
	struct lifo_struct *next;
	} lifo;

/******************************** FUNCTIONS *******************************/

void reset_cgi_vars(void);
void cgi_init(void (*doc_header)(int), void (*doc_footer)(void), int object_options, int status_options);
void free_memory(void);

const char *get_cgi_config_location(void);				/* gets location of the CGI config file to read */
const char *get_cmd_file_location(void);				/* gets location of external command file to write to */

int read_cgi_config_file(const char *);
int read_main_config_file(const char *);
int read_all_object_configuration_data(const char *, int);
int read_all_status_data(const char *, int);

char *unescape_newlines(char *);
void sanitize_plugin_output(char *);                            /* strips HTML and bad characters from plugin output */
void strip_html_brackets(char *);				/* strips > and < from string */

void get_time_string(time_t *, char *, int, int);			/* gets a date/time string */
void get_interval_time_string(double, char *, int);		/* gets a time string for an interval of time */

const char *url_encode(const char *);		        		/* encodes a string in proper URL format */
char *html_encode(char *, int);					/* encodes a string in HTML format (for what the user sees) */
char *escape_string(const char *);					/* escape string for html form usage */

void get_log_archive_to_use(int, char *, int);			/* determines the name of the log archive to use */
void determine_log_rotation_times(int);
int determine_archive_to_use_from_time(time_t);

void print_extra_hostgroup_url(char *, char *);
void print_extra_servicegroup_url(char *, char *);

void display_info_table(const char *, int, authdata *);
void display_nav_table(char *, int);

void display_splunk_host_url(host *);
void display_splunk_service_url(service *);
void display_splunk_generic_url(char *, int);
void strip_splunk_query_terms(char *);

void include_ssi_files(const char *, int);                            /* include user-defined SSI footers/headers */
void include_ssi_file(const char *);                                  /* include user-defined SSI footer/header */

void cgi_config_file_error(const char *);
void main_config_file_error(const char *);
void object_data_error(void);
void status_data_error(void);

void display_context_help(const char *);				/* displays context-sensitive help window */

int read_file_into_lifo(char *);				/* LIFO functions */
void free_lifo_memory(void);
int push_lifo(char *);
char *pop_lifo(void);

NAGIOS_END_DECL
#endif
