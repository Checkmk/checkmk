/************************************************************************
 *
 * Nagios Common Header File
 * Written By: Ethan Galstad (egalstad@nagios.org)
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

#ifndef INCLUDE_COMMON_H
#define INCLUDE_COMMON_H

#include "shared.h"

#define PROGRAM_VERSION "4.0.2"
#define PROGRAM_MODIFICATION_DATE "11-25-2013"

NAGIOS_BEGIN_DECL

/*************************************************************/
/************** SHARED GLOBAL VARIABLES **********************/
/*************************************************************/
extern int date_format;
extern int interval_length;
extern char *illegal_output_chars;
extern char illegal_output_char_map[256];

extern int log_rotation_method;
extern int check_external_commands;
/* set this if you're going to add a ton of comments at once */
extern int defer_comment_sorting;
extern unsigned long next_downtime_id;

extern char *object_cache_file;
extern char *status_file;

extern time_t program_start;
extern int nagios_pid;
extern int daemon_mode;

extern time_t last_log_rotation;

extern int process_performance_data;
extern int enable_flap_detection;
extern int enable_notifications;
extern int execute_service_checks;
extern int accept_passive_service_checks;
extern int execute_host_checks;
extern int accept_passive_host_checks;
extern int enable_event_handlers;
extern int obsess_over_services;
extern int obsess_over_hosts;

extern int enable_timing_point;

extern char *config_file_dir;

#ifdef HAVE_TZNAME
#ifdef CYGWIN
extern char     *_tzname[2] __declspec(dllimport);
#else
extern char     *tzname[2];
#endif
#endif


NAGIOS_END_DECL


/* Experimental performance tweaks - use with caution */
#undef USE_MEMORY_PERFORMANCE_TWEAKS


/****************** OBJECT STATES ********************/
#define STATE_OK			0
#define STATE_WARNING			1
#define STATE_CRITICAL			2
#define STATE_UNKNOWN			3
#define STATE_UP                0
#define STATE_DOWN              1
#define STATE_UNREACHABLE       2
/* for legacy reasons */
#define HOST_UP              STATE_UP
#define HOST_DOWN            STATE_DOWN
#define HOST_UNREACHABLE     STATE_UNREACHABLE

/***************************** COMMANDS *********************************/

#define CMD_NONE			0

#define CMD_ADD_HOST_COMMENT		1
#define CMD_DEL_HOST_COMMENT		2

#define CMD_ADD_SVC_COMMENT		3
#define CMD_DEL_SVC_COMMENT		4

#define CMD_ENABLE_SVC_CHECK		5
#define CMD_DISABLE_SVC_CHECK		6

#define CMD_SCHEDULE_SVC_CHECK		7

#define CMD_DELAY_SVC_NOTIFICATION	9

#define CMD_DELAY_HOST_NOTIFICATION	10

#define CMD_DISABLE_NOTIFICATIONS	11
#define CMD_ENABLE_NOTIFICATIONS	12

#define CMD_RESTART_PROCESS		13
#define CMD_SHUTDOWN_PROCESS		14

#define CMD_ENABLE_HOST_SVC_CHECKS              15
#define CMD_DISABLE_HOST_SVC_CHECKS             16

#define CMD_SCHEDULE_HOST_SVC_CHECKS            17

#define CMD_DELAY_HOST_SVC_NOTIFICATIONS        19  /* currently unimplemented */

#define CMD_DEL_ALL_HOST_COMMENTS               20
#define CMD_DEL_ALL_SVC_COMMENTS                21

#define CMD_ENABLE_SVC_NOTIFICATIONS                    22
#define CMD_DISABLE_SVC_NOTIFICATIONS                   23
#define CMD_ENABLE_HOST_NOTIFICATIONS                   24
#define CMD_DISABLE_HOST_NOTIFICATIONS                  25
#define CMD_ENABLE_ALL_NOTIFICATIONS_BEYOND_HOST        26
#define CMD_DISABLE_ALL_NOTIFICATIONS_BEYOND_HOST       27
#define CMD_ENABLE_HOST_SVC_NOTIFICATIONS		28
#define CMD_DISABLE_HOST_SVC_NOTIFICATIONS		29

#define CMD_PROCESS_SERVICE_CHECK_RESULT		30

#define CMD_SAVE_STATE_INFORMATION			31
#define CMD_READ_STATE_INFORMATION			32

#define CMD_ACKNOWLEDGE_HOST_PROBLEM			33
#define CMD_ACKNOWLEDGE_SVC_PROBLEM			34

#define CMD_START_EXECUTING_SVC_CHECKS			35
#define CMD_STOP_EXECUTING_SVC_CHECKS			36

#define CMD_START_ACCEPTING_PASSIVE_SVC_CHECKS		37
#define CMD_STOP_ACCEPTING_PASSIVE_SVC_CHECKS		38

#define CMD_ENABLE_PASSIVE_SVC_CHECKS			39
#define CMD_DISABLE_PASSIVE_SVC_CHECKS			40

#define CMD_ENABLE_EVENT_HANDLERS			41
#define CMD_DISABLE_EVENT_HANDLERS			42

#define CMD_ENABLE_HOST_EVENT_HANDLER			43
#define CMD_DISABLE_HOST_EVENT_HANDLER			44

#define CMD_ENABLE_SVC_EVENT_HANDLER			45
#define CMD_DISABLE_SVC_EVENT_HANDLER			46

#define CMD_ENABLE_HOST_CHECK				47
#define CMD_DISABLE_HOST_CHECK				48

#define CMD_START_OBSESSING_OVER_SVC_CHECKS		49
#define CMD_STOP_OBSESSING_OVER_SVC_CHECKS		50

#define CMD_REMOVE_HOST_ACKNOWLEDGEMENT			51
#define CMD_REMOVE_SVC_ACKNOWLEDGEMENT			52

#define CMD_SCHEDULE_FORCED_HOST_SVC_CHECKS             53
#define CMD_SCHEDULE_FORCED_SVC_CHECK                   54

#define CMD_SCHEDULE_HOST_DOWNTIME                      55
#define CMD_SCHEDULE_SVC_DOWNTIME                       56

#define CMD_ENABLE_HOST_FLAP_DETECTION                  57
#define CMD_DISABLE_HOST_FLAP_DETECTION                 58

#define CMD_ENABLE_SVC_FLAP_DETECTION                   59
#define CMD_DISABLE_SVC_FLAP_DETECTION                  60

#define CMD_ENABLE_FLAP_DETECTION                       61
#define CMD_DISABLE_FLAP_DETECTION                      62

#define CMD_ENABLE_HOSTGROUP_SVC_NOTIFICATIONS          63
#define CMD_DISABLE_HOSTGROUP_SVC_NOTIFICATIONS         64

#define CMD_ENABLE_HOSTGROUP_HOST_NOTIFICATIONS         65
#define CMD_DISABLE_HOSTGROUP_HOST_NOTIFICATIONS        66

#define CMD_ENABLE_HOSTGROUP_SVC_CHECKS                 67
#define CMD_DISABLE_HOSTGROUP_SVC_CHECKS                68

/* commands 69-77 are unimplemented */
#define CMD_UNIMPLEMENTED_69                            69
#define CMD_UNIMPLEMENTED_70                            70
#define CMD_UNIMPLEMENTED_71                            71
#define CMD_UNIMPLEMENTED_72                            72
#define CMD_UNIMPLEMENTED_73                            73
#define CMD_UNIMPLEMENTED_74                            74
#define CMD_UNIMPLEMENTED_75                            75
#define CMD_UNIMPLEMENTED_76                            76
#define CMD_UNIMPLEMENTED_77                            77

#define CMD_DEL_HOST_DOWNTIME                           78
#define CMD_DEL_SVC_DOWNTIME                            79

#define CMD_ENABLE_PERFORMANCE_DATA                     82
#define CMD_DISABLE_PERFORMANCE_DATA                    83

#define CMD_SCHEDULE_HOSTGROUP_HOST_DOWNTIME            84
#define CMD_SCHEDULE_HOSTGROUP_SVC_DOWNTIME             85
#define CMD_SCHEDULE_HOST_SVC_DOWNTIME                  86

/* new commands in Nagios 2.x found below... */
#define CMD_PROCESS_HOST_CHECK_RESULT		        87

#define CMD_START_EXECUTING_HOST_CHECKS			88
#define CMD_STOP_EXECUTING_HOST_CHECKS			89

#define CMD_START_ACCEPTING_PASSIVE_HOST_CHECKS		90
#define CMD_STOP_ACCEPTING_PASSIVE_HOST_CHECKS		91

#define CMD_ENABLE_PASSIVE_HOST_CHECKS			92
#define CMD_DISABLE_PASSIVE_HOST_CHECKS			93

#define CMD_START_OBSESSING_OVER_HOST_CHECKS		94
#define CMD_STOP_OBSESSING_OVER_HOST_CHECKS		95

#define CMD_SCHEDULE_HOST_CHECK		                96
#define CMD_SCHEDULE_FORCED_HOST_CHECK                  98

#define CMD_START_OBSESSING_OVER_SVC		        99
#define CMD_STOP_OBSESSING_OVER_SVC		        100

#define CMD_START_OBSESSING_OVER_HOST		        101
#define CMD_STOP_OBSESSING_OVER_HOST		        102

#define CMD_ENABLE_HOSTGROUP_HOST_CHECKS                103
#define CMD_DISABLE_HOSTGROUP_HOST_CHECKS               104

#define CMD_ENABLE_HOSTGROUP_PASSIVE_SVC_CHECKS         105
#define CMD_DISABLE_HOSTGROUP_PASSIVE_SVC_CHECKS        106

#define CMD_ENABLE_HOSTGROUP_PASSIVE_HOST_CHECKS        107
#define CMD_DISABLE_HOSTGROUP_PASSIVE_HOST_CHECKS       108

#define CMD_ENABLE_SERVICEGROUP_SVC_NOTIFICATIONS       109
#define CMD_DISABLE_SERVICEGROUP_SVC_NOTIFICATIONS      110

#define CMD_ENABLE_SERVICEGROUP_HOST_NOTIFICATIONS      111
#define CMD_DISABLE_SERVICEGROUP_HOST_NOTIFICATIONS     112

#define CMD_ENABLE_SERVICEGROUP_SVC_CHECKS              113
#define CMD_DISABLE_SERVICEGROUP_SVC_CHECKS             114

#define CMD_ENABLE_SERVICEGROUP_HOST_CHECKS             115
#define CMD_DISABLE_SERVICEGROUP_HOST_CHECKS            116

#define CMD_ENABLE_SERVICEGROUP_PASSIVE_SVC_CHECKS      117
#define CMD_DISABLE_SERVICEGROUP_PASSIVE_SVC_CHECKS     118

#define CMD_ENABLE_SERVICEGROUP_PASSIVE_HOST_CHECKS     119
#define CMD_DISABLE_SERVICEGROUP_PASSIVE_HOST_CHECKS    120

#define CMD_SCHEDULE_SERVICEGROUP_HOST_DOWNTIME         121
#define CMD_SCHEDULE_SERVICEGROUP_SVC_DOWNTIME          122

#define CMD_CHANGE_GLOBAL_HOST_EVENT_HANDLER            123
#define CMD_CHANGE_GLOBAL_SVC_EVENT_HANDLER             124

#define CMD_CHANGE_HOST_EVENT_HANDLER                   125
#define CMD_CHANGE_SVC_EVENT_HANDLER                    126

#define CMD_CHANGE_HOST_CHECK_COMMAND                   127
#define CMD_CHANGE_SVC_CHECK_COMMAND                    128

#define CMD_CHANGE_NORMAL_HOST_CHECK_INTERVAL           129
#define CMD_CHANGE_NORMAL_SVC_CHECK_INTERVAL            130
#define CMD_CHANGE_RETRY_SVC_CHECK_INTERVAL             131

#define CMD_CHANGE_MAX_HOST_CHECK_ATTEMPTS              132
#define CMD_CHANGE_MAX_SVC_CHECK_ATTEMPTS               133

#define CMD_SCHEDULE_AND_PROPAGATE_TRIGGERED_HOST_DOWNTIME 134

#define CMD_ENABLE_HOST_AND_CHILD_NOTIFICATIONS         135
#define CMD_DISABLE_HOST_AND_CHILD_NOTIFICATIONS        136

#define CMD_SCHEDULE_AND_PROPAGATE_HOST_DOWNTIME        137

#define CMD_ENABLE_SERVICE_FRESHNESS_CHECKS             138
#define CMD_DISABLE_SERVICE_FRESHNESS_CHECKS            139

#define CMD_ENABLE_HOST_FRESHNESS_CHECKS                140
#define CMD_DISABLE_HOST_FRESHNESS_CHECKS               141

#define CMD_SET_HOST_NOTIFICATION_NUMBER                142
#define CMD_SET_SVC_NOTIFICATION_NUMBER                 143

/* new commands in Nagios 3.x found below... */
#define CMD_CHANGE_HOST_CHECK_TIMEPERIOD                144
#define CMD_CHANGE_SVC_CHECK_TIMEPERIOD                 145

#define CMD_PROCESS_FILE                                146

#define CMD_CHANGE_CUSTOM_HOST_VAR                      147
#define CMD_CHANGE_CUSTOM_SVC_VAR                       148
#define CMD_CHANGE_CUSTOM_CONTACT_VAR                   149

#define CMD_ENABLE_CONTACT_HOST_NOTIFICATIONS           150
#define CMD_DISABLE_CONTACT_HOST_NOTIFICATIONS          151
#define CMD_ENABLE_CONTACT_SVC_NOTIFICATIONS            152
#define CMD_DISABLE_CONTACT_SVC_NOTIFICATIONS           153

#define CMD_ENABLE_CONTACTGROUP_HOST_NOTIFICATIONS      154
#define CMD_DISABLE_CONTACTGROUP_HOST_NOTIFICATIONS     155
#define CMD_ENABLE_CONTACTGROUP_SVC_NOTIFICATIONS       156
#define CMD_DISABLE_CONTACTGROUP_SVC_NOTIFICATIONS      157

#define CMD_CHANGE_RETRY_HOST_CHECK_INTERVAL            158

#define CMD_SEND_CUSTOM_HOST_NOTIFICATION               159
#define CMD_SEND_CUSTOM_SVC_NOTIFICATION                160

#define CMD_CHANGE_HOST_NOTIFICATION_TIMEPERIOD         161
#define CMD_CHANGE_SVC_NOTIFICATION_TIMEPERIOD          162
#define CMD_CHANGE_CONTACT_HOST_NOTIFICATION_TIMEPERIOD 163
#define CMD_CHANGE_CONTACT_SVC_NOTIFICATION_TIMEPERIOD  164

#define CMD_CHANGE_HOST_MODATTR                         165
#define CMD_CHANGE_SVC_MODATTR                          166
#define CMD_CHANGE_CONTACT_MODATTR                      167
#define CMD_CHANGE_CONTACT_MODHATTR                     168
#define CMD_CHANGE_CONTACT_MODSATTR                     169

#define CMD_DEL_DOWNTIME_BY_HOST_NAME                   170
#define CMD_DEL_DOWNTIME_BY_HOSTGROUP_NAME              171
#define CMD_DEL_DOWNTIME_BY_START_TIME_COMMENT          172

/* custom command introduced in Nagios 3.x */
#define CMD_CUSTOM_COMMAND                              999

/**************************** COMMAND ERRORS *****************************/
#define CMD_ERROR_OK 0 /* No errors encountered */
#define CMD_ERROR_UNKNOWN_COMMAND 1 /* Unknown/unsupported command */
#define CMD_ERROR_MALFORMED_COMMAND 2 /* Command malformed/missing timestamp? */
#define CMD_ERROR_INTERNAL_ERROR 3 /* Internal error */
#define CMD_ERROR_FAILURE 4 /* Command routine failed */

extern const char *cmd_error_strerror(int error_code);

/**************************** CHECK TYPES ********************************/

#define CHECK_TYPE_ACTIVE   0
#define CHECK_TYPE_PASSIVE  1
#define CHECK_TYPE_PARENT   2 /* (active) check for the benefit of dependent objects */
#define CHECK_TYPE_FILE     3 /* from spool files (yuck) */
#define CHECK_TYPE_OTHER    4 /* for modules to use */


/************* LEGACY (deprecated) CHECK TYPES ***************************/

#define SERVICE_CHECK_ACTIVE    CHECK_TYPE_ACTIVE
#define SERVICE_CHECK_PASSIVE   CHECK_TYPE_PASSIVE
#define HOST_CHECK_ACTIVE       CHECK_TYPE_ACTIVE
#define HOST_CHECK_PASSIVE      CHECK_TYPE_PASSIVE


/************************ SERVICE STATE TYPES ****************************/

#define SOFT_STATE			0
#define HARD_STATE			1


/************************* SCHEDULED DOWNTIME TYPES **********************/

#define SERVICE_DOWNTIME		1	/* service downtime */
#define HOST_DOWNTIME			2	/* host downtime */
#define ANY_DOWNTIME                    3       /* host or service downtime */


/************************** NOTIFICATION OPTIONS *************************/

#define NOTIFICATION_OPTION_NONE        0
#define NOTIFICATION_OPTION_BROADCAST   1
#define NOTIFICATION_OPTION_FORCED      2
#define NOTIFICATION_OPTION_INCREMENT   4


/************************** ACKNOWLEDGEMENT TYPES ************************/

#define HOST_ACKNOWLEDGEMENT            0
#define SERVICE_ACKNOWLEDGEMENT         1

#define ACKNOWLEDGEMENT_NONE            0
#define ACKNOWLEDGEMENT_NORMAL          1
#define ACKNOWLEDGEMENT_STICKY          2


/**************************** DEPENDENCY TYPES ***************************/

#define NOTIFICATION_DEPENDENCY		1
#define EXECUTION_DEPENDENCY		2



/********************** HOST/SERVICE CHECK OPTIONS ***********************/

#define CHECK_OPTION_NONE		0	/* no check options */
#define CHECK_OPTION_FORCE_EXECUTION	1	/* force execution of a check (ignores disabled services/hosts, invalid timeperiods) */
#define CHECK_OPTION_FRESHNESS_CHECK    2       /* this is a freshness check */
#define CHECK_OPTION_ORPHAN_CHECK       4       /* this is an orphan check */
#define CHECK_OPTION_DEPENDENCY_CHECK   8       /* dependency check. different scheduling rules apply */


/**************************** PROGRAM MODES ******************************/

#define STANDBY_MODE		0
#define ACTIVE_MODE		1


/************************** LOG ROTATION MODES ***************************/

#define LOG_ROTATION_NONE       0
#define LOG_ROTATION_HOURLY     1
#define LOG_ROTATION_DAILY      2
#define LOG_ROTATION_WEEKLY     3
#define LOG_ROTATION_MONTHLY    4


/***************************** LOG VERSIONS ******************************/

#define LOG_VERSION_1           "1.0"
#define LOG_VERSION_2           "2.0"



/*************************** CHECK STATISTICS ****************************/

#define ACTIVE_SCHEDULED_SERVICE_CHECK_STATS 0
#define ACTIVE_ONDEMAND_SERVICE_CHECK_STATS  1
#define PASSIVE_SERVICE_CHECK_STATS          2
#define ACTIVE_SCHEDULED_HOST_CHECK_STATS    3
#define ACTIVE_ONDEMAND_HOST_CHECK_STATS     4
#define PASSIVE_HOST_CHECK_STATS             5
#define ACTIVE_CACHED_HOST_CHECK_STATS       6
#define ACTIVE_CACHED_SERVICE_CHECK_STATS    7
#define EXTERNAL_COMMAND_STATS               8
#define PARALLEL_HOST_CHECK_STATS            9
#define SERIAL_HOST_CHECK_STATS              10
#define MAX_CHECK_STATS_TYPES                11


/****************** HOST CONFIG FILE READING OPTIONS ********************/

#define READ_HOSTS			1
#define READ_HOSTGROUPS			2
#define READ_CONTACTS			4
#define READ_CONTACTGROUPS		8
#define READ_SERVICES			16
#define READ_COMMANDS			32
#define READ_TIMEPERIODS		64
#define READ_SERVICEESCALATIONS		128
#define READ_HOSTGROUPESCALATIONS	256     /* no longer implemented */
#define READ_SERVICEDEPENDENCIES        512
#define READ_HOSTDEPENDENCIES           1024
#define READ_HOSTESCALATIONS            2048
#define READ_HOSTEXTINFO                4096
#define READ_SERVICEEXTINFO             8192
#define READ_SERVICEGROUPS              16384

#define READ_ALL_OBJECT_DATA            READ_HOSTS | READ_HOSTGROUPS | READ_CONTACTS | READ_CONTACTGROUPS | READ_SERVICES | READ_COMMANDS | READ_TIMEPERIODS | READ_SERVICEESCALATIONS | READ_SERVICEDEPENDENCIES | READ_HOSTDEPENDENCIES | READ_HOSTESCALATIONS | READ_HOSTEXTINFO | READ_SERVICEEXTINFO | READ_SERVICEGROUPS


/************************** DATE/TIME TYPES *****************************/

#define LONG_DATE_TIME			0
#define SHORT_DATE_TIME			1
#define SHORT_DATE			2
#define SHORT_TIME			3
#define HTTP_DATE_TIME			4	/* time formatted for use in HTTP headers */


/**************************** DATE FORMATS ******************************/

#define DATE_FORMAT_US                  0       /* U.S. (MM-DD-YYYY HH:MM:SS) */
#define DATE_FORMAT_EURO                1       /* European (DD-MM-YYYY HH:MM:SS) */
#define DATE_FORMAT_ISO8601             2       /* ISO8601 (YYYY-MM-DD HH:MM:SS) */
#define DATE_FORMAT_STRICT_ISO8601      3       /* ISO8601 (YYYY-MM-DDTHH:MM:SS) */


/************************** MISC DEFINITIONS ****************************/

#define MAX_FILENAME_LENGTH			256	/* max length of path/filename that Nagios will process */
#define MAX_INPUT_BUFFER			1024	/* size in bytes of max. input buffer (for reading files, misc stuff) */
#define MAX_COMMAND_BUFFER                      8192    /* max length of raw or processed command line */
#define MAX_EXTERNAL_COMMAND_LENGTH             8192    /* max length of an external command */

#define MAX_DATETIME_LENGTH			48


/************************* MODIFIED ATTRIBUTES **************************/

#define MODATTR_NONE                            0
#define MODATTR_NOTIFICATIONS_ENABLED           1
#define MODATTR_ACTIVE_CHECKS_ENABLED           2
#define MODATTR_PASSIVE_CHECKS_ENABLED          4
#define MODATTR_EVENT_HANDLER_ENABLED           8
#define MODATTR_FLAP_DETECTION_ENABLED          16
#define MODATTR_FAILURE_PREDICTION_ENABLED      32
#define MODATTR_PERFORMANCE_DATA_ENABLED        64
#define MODATTR_OBSESSIVE_HANDLER_ENABLED       128
#define MODATTR_EVENT_HANDLER_COMMAND           256
#define MODATTR_CHECK_COMMAND                   512
#define MODATTR_NORMAL_CHECK_INTERVAL           1024
#define MODATTR_RETRY_CHECK_INTERVAL            2048
#define MODATTR_MAX_CHECK_ATTEMPTS              4096
#define MODATTR_FRESHNESS_CHECKS_ENABLED        8192
#define MODATTR_CHECK_TIMEPERIOD                16384
#define MODATTR_CUSTOM_VARIABLE                 32768
#define MODATTR_NOTIFICATION_TIMEPERIOD         65536
#endif /* INCLUDE_COMMON_H */
