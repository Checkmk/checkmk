
/************************************************************************
 *
 * Nagios Main Header File
 * Written By: Ethan Galstad (egalstad@nagios.org)
 * Last Modified: 12-14-2008
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

#ifndef _NAGIOS_H
#define _NAGIOS_H

#ifndef __GNUC__
# define __attribute__(x) /* nothing */
#endif

#include "config.h"
#include "common.h"
#include "locations.h"
#include "objects.h"

#ifdef __cplusplus
extern "C" { 
#endif


/************* MISC LENGTH/SIZE DEFINITIONS ***********/

/* 
   NOTE: Plugin length is artificially capped at 8k to prevent runaway plugins from returning MBs/GBs of data
   back to Nagios.  If you increase the 8k cap by modifying this value, make sure you also increase the value
   of MAX_EXTERNAL_COMMAND_LENGTH in common.h to allow for passive checks results received through the external
   command file. EG 10/19/07
*/
#define MAX_PLUGIN_OUTPUT_LENGTH                8192    /* max length of plugin output (including perf data) */



/******************* DEFAULT VALUES *******************/

#define DEFAULT_LOG_LEVEL					1	/* log all events to main log file */
#define DEFAULT_USE_SYSLOG					1	/* log events to syslog? 1=yes, 0=no */
#define DEFAULT_SYSLOG_LEVEL					2	/* log only severe events to syslog */

#define DEFAULT_NOTIFICATION_LOGGING				1	/* log notification events? 1=yes, 0=no */

#define DEFAULT_INTER_CHECK_DELAY				5.0	/* seconds between initial service check scheduling */
#define DEFAULT_INTERLEAVE_FACTOR      				1       /* default interleave to use when scheduling checks */
#define DEFAULT_SLEEP_TIME      				0.5    	/* seconds between event run checks */
#define DEFAULT_INTERVAL_LENGTH 				60     	/* seconds per interval unit for check scheduling */
#define DEFAULT_RETRY_INTERVAL  				30	/* services are retried in 30 seconds if they're not OK */
#define DEFAULT_COMMAND_CHECK_INTERVAL				-1	/* interval to check for external commands (default = as often as possible) */
#define DEFAULT_CHECK_REAPER_INTERVAL				10	/* interval in seconds to reap host and service check results */
#define DEFAULT_MAX_REAPER_TIME                 		30      /* maximum number of seconds to spend reaping service checks before we break out for a while */
#define DEFAULT_MAX_CHECK_RESULT_AGE				3600    /* maximum number of seconds that a check result file is considered to be valid */
#define DEFAULT_MAX_PARALLEL_SERVICE_CHECKS 			0	/* maximum number of service checks we can have running at any given time (0=unlimited) */
#define DEFAULT_RETENTION_UPDATE_INTERVAL			60	/* minutes between auto-save of retention data */
#define DEFAULT_RETENTION_SCHEDULING_HORIZON    		900     /* max seconds between program restarts that we will preserve scheduling information */
#define DEFAULT_STATUS_UPDATE_INTERVAL				60	/* seconds between aggregated status data updates */
#define DEFAULT_FRESHNESS_CHECK_INTERVAL        		60      /* seconds between service result freshness checks */
#define DEFAULT_AUTO_RESCHEDULING_INTERVAL      		30      /* seconds between host and service check rescheduling events */
#define DEFAULT_AUTO_RESCHEDULING_WINDOW        		180     /* window of time (in seconds) for which we should reschedule host and service checks */
#define DEFAULT_ORPHAN_CHECK_INTERVAL           		60      /* seconds between checks for orphaned hosts and services */

#define DEFAULT_NOTIFICATION_TIMEOUT				30	/* max time in seconds to wait for notification commands to complete */
#define DEFAULT_EVENT_HANDLER_TIMEOUT				30	/* max time in seconds to wait for event handler commands to complete */
#define DEFAULT_HOST_CHECK_TIMEOUT				30	/* max time in seconds to wait for host check commands to complete */
#define DEFAULT_SERVICE_CHECK_TIMEOUT				60	/* max time in seconds to wait for service check commands to complete */
#define DEFAULT_OCSP_TIMEOUT					15	/* max time in seconds to wait for obsessive compulsive processing commands to complete */
#define DEFAULT_OCHP_TIMEOUT					15	/* max time in seconds to wait for obsessive compulsive processing commands to complete */
#define DEFAULT_PERFDATA_TIMEOUT                		5       /* max time in seconds to wait for performance data commands to complete */
#define DEFAULT_TIME_CHANGE_THRESHOLD				900	/* compensate for time changes of more than 15 minutes */

#define DEFAULT_LOG_HOST_RETRIES				0	/* don't log host retries */
#define DEFAULT_LOG_SERVICE_RETRIES				0	/* don't log service retries */
#define DEFAULT_LOG_EVENT_HANDLERS				1	/* log event handlers */
#define DEFAULT_LOG_INITIAL_STATES				0	/* don't log initial service and host states */
#define DEFAULT_LOG_EXTERNAL_COMMANDS				1	/* log external commands */
#define DEFAULT_LOG_PASSIVE_CHECKS				1	/* log passive service checks */

#define DEFAULT_DEBUG_LEVEL                                     0       /* don't log any debugging information */
#define DEFAULT_DEBUG_VERBOSITY                                 1
#define DEFAULT_MAX_DEBUG_FILE_SIZE                             1000000 /* max size of debug log */

#define DEFAULT_AGGRESSIVE_HOST_CHECKING			0	/* don't use "aggressive" host checking */
#define DEFAULT_CHECK_EXTERNAL_COMMANDS				1 	/* check for external commands */
#define DEFAULT_CHECK_ORPHANED_SERVICES				1	/* check for orphaned services */
#define DEFAULT_CHECK_ORPHANED_HOSTS            		1       /* check for orphaned hosts */
#define DEFAULT_ENABLE_FLAP_DETECTION           		0       /* don't enable flap detection */
#define DEFAULT_PROCESS_PERFORMANCE_DATA        		0       /* don't process performance data */
#define DEFAULT_CHECK_SERVICE_FRESHNESS         		1       /* check service result freshness */
#define DEFAULT_CHECK_HOST_FRESHNESS            		0       /* don't check host result freshness */
#define DEFAULT_AUTO_RESCHEDULE_CHECKS          		0       /* don't auto-reschedule host and service checks */
#define DEFAULT_TRANSLATE_PASSIVE_HOST_CHECKS                   0       /* should we translate DOWN/UNREACHABLE passive host checks? */
#define DEFAULT_PASSIVE_HOST_CHECKS_SOFT                        0       /* passive host checks are treated as HARD by default */

#define DEFAULT_LOW_SERVICE_FLAP_THRESHOLD			20.0	/* low threshold for detection of service flapping */
#define DEFAULT_HIGH_SERVICE_FLAP_THRESHOLD			30.0	/* high threshold for detection of service flapping */
#define DEFAULT_LOW_HOST_FLAP_THRESHOLD				20.0	/* low threshold for detection of host flapping */
#define DEFAULT_HIGH_HOST_FLAP_THRESHOLD			30.0	/* high threshold for detection of host flapping */

#define DEFAULT_HOST_CHECK_SPREAD				30	/* max minutes to schedule all initial host checks */
#define DEFAULT_SERVICE_CHECK_SPREAD				30	/* max minutes to schedule all initial service checks */

#define DEFAULT_CACHED_HOST_CHECK_HORIZON      			15      /* max age in seconds that cached host checks can be used */
#define DEFAULT_CACHED_SERVICE_CHECK_HORIZON    		15      /* max age in seconds that cached service checks can be used */
#define DEFAULT_ENABLE_PREDICTIVE_HOST_DEPENDENCY_CHECKS	1	/* should we use predictive host dependency checks? */
#define DEFAULT_ENABLE_PREDICTIVE_SERVICE_DEPENDENCY_CHECKS	1	/* should we use predictive service dependency checks? */

#define DEFAULT_USE_LARGE_INSTALLATION_TWEAKS                   0       /* don't use tweaks for large Nagios installations */

#define DEFAULT_ENABLE_EMBEDDED_PERL                            0       /* enable embedded Perl interpreter (if compiled in) */
#define DEFAULT_USE_EMBEDDED_PERL_IMPLICITLY                    1       /* by default, embedded Perl is used for Perl plugins that don't explicitly disable it */

#define DEFAULT_ADDITIONAL_FRESHNESS_LATENCY			15	/* seconds to be added to freshness thresholds when automatically calculated by Nagios */

#define DEFAULT_CHECK_FOR_UPDATES                               1       /* should we check for new Nagios releases? */
#define DEFAULT_BARE_UPDATE_CHECK                               0       /* report current version and new installs */
#define MINIMUM_UPDATE_CHECK_INTERVAL                           60*60*22 /* 22 hours minimum between checks - please be kind to our servers! */
#define BASE_UPDATE_CHECK_INTERVAL                              60*60*22 /* 22 hours base interval */
#define UPDATE_CHECK_INTERVAL_WOBBLE                            60*60*4  /* 4 hour wobble on top of base interval */
#define BASE_UPDATE_CHECK_RETRY_INTERVAL                        60*60*1  /* 1 hour base retry interval */
#define UPDATE_CHECK_RETRY_INTERVAL_WOBBLE                      60*60*3  /* 3 hour wobble on top of base retry interval */


/******************* LOGGING TYPES ********************/

#define NSLOG_RUNTIME_ERROR		1
#define NSLOG_RUNTIME_WARNING		2

#define NSLOG_VERIFICATION_ERROR	4
#define NSLOG_VERIFICATION_WARNING	8

#define NSLOG_CONFIG_ERROR		16
#define NSLOG_CONFIG_WARNING		32

#define NSLOG_PROCESS_INFO		64
#define NSLOG_EVENT_HANDLER		128
/*#define NSLOG_NOTIFICATION		256*/	/* NOT USED ANYMORE - CAN BE REUSED */
#define NSLOG_EXTERNAL_COMMAND		512

#define NSLOG_HOST_UP      		1024
#define NSLOG_HOST_DOWN			2048
#define NSLOG_HOST_UNREACHABLE		4096

#define NSLOG_SERVICE_OK		8192
#define NSLOG_SERVICE_UNKNOWN		16384
#define NSLOG_SERVICE_WARNING		32768
#define NSLOG_SERVICE_CRITICAL		65536

#define NSLOG_PASSIVE_CHECK		131072

#define NSLOG_INFO_MESSAGE		262144

#define NSLOG_HOST_NOTIFICATION		524288
#define NSLOG_SERVICE_NOTIFICATION	1048576


/***************** DEBUGGING LEVELS *******************/

#define DEBUGL_ALL                      -1
#define DEBUGL_NONE                     0
#define DEBUGL_FUNCTIONS                1
#define DEBUGL_CONFIG			2
#define DEBUGL_PROCESS                  4
#define DEBUGL_STATUSDATA               4
#define DEBUGL_RETENTIONDATA            4
#define DEBUGL_EVENTS                   8
#define DEBUGL_CHECKS                   16
#define DEBUGL_IPC                      16
#define DEBUGL_FLAPPING                 16
#define DEBUGL_EVENTHANDLERS            16
#define DEBUGL_PERFDATA                 16
#define DEBUGL_NOTIFICATIONS            32
#define DEBUGL_EVENTBROKER              64
#define DEBUGL_EXTERNALCOMMANDS         128
#define DEBUGL_COMMANDS                 256
#define DEBUGL_DOWNTIME                 512
#define DEBUGL_COMMENTS                 1024
#define DEBUGL_MACROS                   2048

#define DEBUGV_BASIC                    0
#define DEBUGV_MORE			1
#define DEBUGV_MOST                     2


/******************** HOST STATUS *********************/

#define HOST_UP				0
#define HOST_DOWN			1
#define HOST_UNREACHABLE		2	



/******************* STATE LOGGING TYPES **************/

#define INITIAL_STATES                  1
#define CURRENT_STATES                  2



/************ SERVICE DEPENDENCY VALUES ***************/

#define DEPENDENCIES_OK			0
#define DEPENDENCIES_FAILED		1



/*********** ROUTE CHECK PROPAGATION TYPES ************/

#define PROPAGATE_TO_PARENT_HOSTS	1
#define PROPAGATE_TO_CHILD_HOSTS	2



/****************** SERVICE STATES ********************/

#define STATE_OK			0
#define STATE_WARNING			1
#define STATE_CRITICAL			2
#define STATE_UNKNOWN			3       /* changed from -1 on 02/24/2001 */



/****************** FLAPPING TYPES ********************/

#define HOST_FLAPPING                   0
#define SERVICE_FLAPPING                1



/**************** NOTIFICATION TYPES ******************/

#define HOST_NOTIFICATION               0
#define SERVICE_NOTIFICATION            1



/************* NOTIFICATION REASON TYPES ***************/

#define NOTIFICATION_NORMAL             0
#define NOTIFICATION_ACKNOWLEDGEMENT    1
#define NOTIFICATION_FLAPPINGSTART      2
#define NOTIFICATION_FLAPPINGSTOP       3
#define NOTIFICATION_FLAPPINGDISABLED   4
#define NOTIFICATION_DOWNTIMESTART      5
#define NOTIFICATION_DOWNTIMEEND        6
#define NOTIFICATION_DOWNTIMECANCELLED  7
#define NOTIFICATION_CUSTOM             99



/**************** EVENT HANDLER TYPES *****************/

#define HOST_EVENTHANDLER               0
#define SERVICE_EVENTHANDLER            1
#define GLOBAL_HOST_EVENTHANDLER        2
#define GLOBAL_SERVICE_EVENTHANDLER     3



/***************** STATE CHANGE TYPES *****************/

#define HOST_STATECHANGE                0
#define SERVICE_STATECHANGE             1



/***************** OBJECT CHECK TYPES *****************/
#define SERVICE_CHECK                   0
#define HOST_CHECK                      1



/******************* EVENT TYPES **********************/

#define EVENT_SERVICE_CHECK		0	/* active service check */
#define EVENT_COMMAND_CHECK		1	/* external command check */
#define EVENT_LOG_ROTATION		2	/* log file rotation */
#define EVENT_PROGRAM_SHUTDOWN		3	/* program shutdown */
#define EVENT_PROGRAM_RESTART		4	/* program restart */
#define EVENT_CHECK_REAPER              5       /* reaps results from host and service checks */
#define EVENT_ORPHAN_CHECK		6	/* checks for orphaned hosts and services */
#define EVENT_RETENTION_SAVE		7	/* save (dump) retention data */
#define EVENT_STATUS_SAVE		8	/* save (dump) status data */
#define EVENT_SCHEDULED_DOWNTIME	9	/* scheduled host or service downtime */
#define EVENT_SFRESHNESS_CHECK          10      /* checks service result "freshness" */
#define EVENT_EXPIRE_DOWNTIME		11      /* checks for (and removes) expired scheduled downtime */
#define EVENT_HOST_CHECK                12      /* active host check */
#define EVENT_HFRESHNESS_CHECK          13      /* checks host result "freshness" */
#define EVENT_RESCHEDULE_CHECKS		14      /* adjust scheduling of host and service checks */
#define EVENT_EXPIRE_COMMENT            15      /* removes expired comments */
#define EVENT_CHECK_PROGRAM_UPDATE      16      /* checks for new version of Nagios */
#define EVENT_SLEEP                     98      /* asynchronous sleep event that occurs when event queues are empty */
#define EVENT_USER_FUNCTION             99      /* USER-defined function (modules) */



/******* INTER-CHECK DELAY CALCULATION TYPES **********/

#define ICD_NONE			0	/* no inter-check delay */
#define ICD_DUMB			1	/* dumb delay of 1 second */
#define ICD_SMART			2	/* smart delay */
#define ICD_USER			3       /* user-specified delay */



/******* INTERLEAVE FACTOR CALCULATION TYPES **********/

#define ILF_USER			0	/* user-specified interleave factor */
#define ILF_SMART			1	/* smart interleave */



/************ SCHEDULED DOWNTIME TYPES ****************/

#define ACTIVE_DOWNTIME                 0       /* active downtime - currently in effect */
#define PENDING_DOWNTIME                1       /* pending downtime - scheduled for the future */



/****************** DATA STRUCTURES *******************/

/* TIMED_EVENT structure */
typedef struct timed_event_struct{
	int event_type;
	time_t run_time;
	int recurring;
	unsigned long event_interval;
	int compensate_for_time_change;
	void *timing_func;
	void *event_data;
	void *event_args;
	int event_options;
        struct timed_event_struct *next;
        struct timed_event_struct *prev;
        }timed_event;


/* NOTIFY_LIST structure */
typedef struct notify_list_struct{
	contact *this_should_be_named_other_than_contact;
	struct notify_list_struct *next;
        }notification;


/* CHECK_RESULT structure */
typedef struct check_result_struct{
	int object_check_type;                          /* is this a service or a host check? */
	char *host_name;                                /* host name */
	char *service_description;                      /* service description */
	int check_type;					/* was this an active or passive service check? */
	int check_options;         
	int scheduled_check;                            /* was this a scheduled or an on-demand check? */
	int reschedule_check;                           /* should we reschedule the next check */
	char *output_file;                              /* what file is the output stored in? */
	FILE *output_file_fp;
	int output_file_fd;
	double latency;
	struct timeval start_time;			/* time the service check was initiated */
	struct timeval finish_time;			/* time the service check was completed */
	int early_timeout;                              /* did the service check timeout? */
	int exited_ok;					/* did the plugin check return okay? */
	int return_code;				/* plugin return code */
	char *output;	                                /* plugin output */
	struct check_result_struct *next;
	}check_result;


/* SCHED_INFO structure */
typedef struct sched_info_struct{
	int total_services;
	int total_scheduled_services;
	int total_hosts;
	int total_scheduled_hosts;
	double average_services_per_host;
	double average_scheduled_services_per_host;
	unsigned long service_check_interval_total;
	unsigned long host_check_interval_total;
	double average_service_execution_time;
	double average_service_check_interval;
	double average_host_check_interval;
	double average_service_inter_check_delay;
	double average_host_inter_check_delay;
	double service_inter_check_delay;
	double host_inter_check_delay;
	int service_interleave_factor;
	int max_service_check_spread;
	int max_host_check_spread;
	time_t first_service_check;
	time_t last_service_check;
	time_t first_host_check;
	time_t last_host_check;
        }sched_info;


/* PASSIVE_CHECK_RESULT structure */
typedef struct passive_check_result_struct{
	int object_check_type;
	char *host_name;
	char *service_description;
	int return_code;
	char *output;
	time_t check_time;
	double latency;
	struct passive_check_result_struct *next;
	}passive_check_result;


/* CIRCULAR_BUFFER structure - used by worker threads */
typedef struct circular_buffer_struct{
	void            **buffer;
	int             tail;
	int             head;
	int             items;
	int		high;		/* highest number of items that has ever been stored in buffer */
	unsigned long   overflow;
	pthread_mutex_t buffer_lock;
        }circular_buffer;


/* MMAPFILE structure - used for reading files via mmap() */
typedef struct mmapfile_struct{
	char *path;
	int mode;
	int fd;
	unsigned long file_size;
	unsigned long current_position;
	unsigned long current_line;
	void *mmap_buf;
        }mmapfile;


/* DBUF structure - dynamic string storage */
typedef struct dbuf_struct{
	char *buf;
	unsigned long used_size;
	unsigned long allocated_size;
	unsigned long chunk_size;
        }dbuf;


#define CHECK_STATS_BUCKETS                  15

/* used for tracking host and service check statistics */
typedef struct check_stats_struct{
	int current_bucket;
	int bucket[CHECK_STATS_BUCKETS];
	int overflow_bucket;
	int minute_stats[3];
	time_t last_update;
        }check_stats;


/******************* THREAD STUFF ********************/

/* slots in circular buffers */
#define DEFAULT_EXTERNAL_COMMAND_BUFFER_SLOTS     4096

/* worker threads */
#define TOTAL_WORKER_THREADS              1

#define COMMAND_WORKER_THREAD		  0



/******************** FUNCTIONS **********************/

/**** Configuration Functions ****/
int read_main_config_file(char *);                     		/* reads the main config file (nagios.cfg) */
int read_resource_file(char *);					/* processes macros in resource file */
int read_all_object_data(char *);				/* reads all object config data */


/**** Setup Functions ****/
int pre_flight_check(void);                          		/* try and verify the configuration data */
int pre_flight_object_check(int *,int *);               	/* verify object relationships and settings */
int pre_flight_circular_check(int *,int *);             	/* detects circular dependencies and paths */
void init_timing_loop(void);                         		/* setup the initial scheduling queue */
void setup_sighandler(void);                         		/* trap signals */
void reset_sighandler(void);                         		/* reset signals to default action */
int daemon_init(void);				     		/* switches to daemon mode */
int drop_privileges(char *,char *);				/* drops privileges before startup */
void display_scheduling_info(void);				/* displays service check scheduling information */


/**** Event Queue Functions ****/
int schedule_new_event(int,int,time_t,int,unsigned long,void *,int,void *,void *,int);	/* schedules a new timed event */
void reschedule_event(timed_event *,timed_event **,timed_event **);   		/* reschedules an event */
void add_event(timed_event *,timed_event **,timed_event **);     		/* adds an event to the execution queue */
void remove_event(timed_event *,timed_event **,timed_event **);     		/* remove an event from the execution queue */
int event_execution_loop(void);                      		/* main monitoring/event handler loop */
int handle_timed_event(timed_event *);		     		/* top level handler for timed events */
void adjust_check_scheduling(void);		        	/* auto-adjusts scheduling of host and service checks */
void compensate_for_system_time_change(unsigned long,unsigned long);	/* attempts to compensate for a change in the system time */
void adjust_timestamp_for_time_change(time_t,time_t,unsigned long,time_t *); /* adjusts a timestamp variable for a system time change */
void resort_event_list(timed_event **,timed_event **);                 	/* resorts event list by event run time for system time changes */


/**** IPC Functions ****/
int move_check_result_to_queue(char *);
int process_check_result_queue(char *);
int process_check_result_file(char *);
int add_check_result_to_list(check_result *);
check_result *read_check_result(void);                  	/* reads a host/service check result from the list in memory */
int delete_check_result_file(char *);
int free_check_result_list(void);
int init_check_result(check_result *);
int free_check_result(check_result *);                  	/* frees memory associated with a host/service check result */
int parse_check_output(char *,char **,char **,char **,int,int);
int open_command_file(void);					/* creates the external command file as a named pipe (FIFO) and opens it for reading */
int close_command_file(void);					/* closes and deletes the external command file (FIFO) */


/**** Monitoring/Event Handler Functions ****/
int check_service_dependencies(service *,int);          	/* checks service dependencies */
int check_host_dependencies(host *,int);                	/* checks host dependencies */
void check_for_orphaned_services(void);				/* checks for orphaned services */
void check_for_orphaned_hosts(void);				/* checks for orphaned hosts */
void check_service_result_freshness(void);              	/* checks the "freshness" of service check results */
int is_service_result_fresh(service *,time_t,int);              /* determines if a service's check results are fresh */
void check_host_result_freshness(void);                 	/* checks the "freshness" of host check results */
int is_host_result_fresh(host *,time_t,int);                    /* determines if a host's check results are fresh */
int my_system(char *,int,int *,double *,char **,int);         	/* executes a command via popen(), but also protects against timeouts */


/**** Flap Detection Functions ****/
void check_for_service_flapping(service *,int,int);	        /* determines whether or not a service is "flapping" between states */
void check_for_host_flapping(host *,int,int,int);		/* determines whether or not a host is "flapping" between states */
void set_service_flap(service *,double,double,double,int);	/* handles a service that is flapping */
void clear_service_flap(service *,double,double,double);	/* handles a service that has stopped flapping */
void set_host_flap(host *,double,double,double,int);		/* handles a host that is flapping */
void clear_host_flap(host *,double,double,double);		/* handles a host that has stopped flapping */
void enable_flap_detection_routines(void);			/* enables flap detection on a program-wide basis */
void disable_flap_detection_routines(void);			/* disables flap detection on a program-wide basis */
void enable_host_flap_detection(host *);			/* enables flap detection for a particular host */
void disable_host_flap_detection(host *);			/* disables flap detection for a particular host */
void enable_service_flap_detection(service *);			/* enables flap detection for a particular service */
void disable_service_flap_detection(service *);			/* disables flap detection for a particular service */
void handle_host_flap_detection_disabled(host *);		/* handles the details when flap detection is disabled globally or on a per-host basis */
void handle_service_flap_detection_disabled(service *);		/* handles the details when flap detection is disabled globally or on a per-service basis */


/**** Route/Host Check Functions ****/
int perform_on_demand_host_check(host *,int *,int,int,unsigned long);
int perform_scheduled_host_check(host *,int,double);
int check_host_check_viability_3x(host *,int,int *,time_t *);
int adjust_host_check_attempt_3x(host *,int);
int determine_host_reachability(host *);
int process_host_check_result_3x(host *,int,char *,int,int,int,unsigned long);
int perform_on_demand_host_check_3x(host *,int *,int,int,unsigned long);
int run_sync_host_check_3x(host *,int *,int,int,unsigned long);
int execute_sync_host_check_3x(host *);
int run_scheduled_host_check_3x(host *,int,double);
int run_async_host_check_3x(host *,int,double,int,int,int *,time_t *);
int handle_async_host_check_result_3x(host *,check_result *);


/**** Service Check Functions ****/
int check_service_check_viability(service *,int,int *,time_t *);
int run_scheduled_service_check(service *,int,double);
int run_async_service_check(service *,int,double,int,int,int *,time_t *);
int handle_async_service_check_result(service *,check_result *);


/**** Event Handler Functions ****/
int handle_host_state(host *);               			/* top level host state handler */



/**** Common Check Fucntions *****/
int reap_check_results(void);


/**** Check Statistics Functions ****/
int init_check_stats(void);
int update_check_stats(int,time_t);
int generate_check_stats(void);



/**** Event Handler Functions ****/
int obsessive_compulsive_service_check_processor(service *);	/* distributed monitoring craziness... */
int obsessive_compulsive_host_check_processor(host *);		/* distributed monitoring craziness... */
int handle_service_event(service *);				/* top level service event logic */
int run_service_event_handler(service *);			/* runs the event handler for a specific service */
int run_global_service_event_handler(service *);		/* runs the global service event handler */
int handle_host_event(host *);					/* top level host event logic */
int run_host_event_handler(host *);				/* runs the event handler for a specific host */
int run_global_host_event_handler(host *);			/* runs the global host event handler */


/**** Notification Functions ****/
int check_service_notification_viability(service *,int,int);			/* checks viability of notifying all contacts about a service */
int is_valid_escalation_for_service_notification(service *,serviceescalation *,int);	/* checks if an escalation entry is valid for a particular service notification */
int should_service_notification_be_escalated(service *);			/* checks if a service notification should be escalated */
int service_notification(service *,int,char *,char *,int);                     	/* notify all contacts about a service (problem or recovery) */
int check_contact_service_notification_viability(contact *,service *,int,int);	/* checks viability of notifying a contact about a service */ 
int notify_contact_of_service(contact *,service *,int,char *,char *,int,int);  	/* notify a single contact about a service */
int check_host_notification_viability(host *,int,int);				/* checks viability of notifying all contacts about a host */
int is_valid_escalation_for_host_notification(host *,hostescalation *,int);	/* checks if an escalation entry is valid for a particular host notification */
int should_host_notification_be_escalated(host *);				/* checks if a host notification should be escalated */
int host_notification(host *,int,char *,char *,int);                           	/* notify all contacts about a host (problem or recovery) */
int check_contact_host_notification_viability(contact *,host *,int,int);	/* checks viability of notifying a contact about a host */ 
int notify_contact_of_host(contact *,host *,int,char *,char *,int,int);        	/* notify a single contact about a host */
int create_notification_list_from_host(host *,int,int *);         		/* given a host, create list of contacts to be notified (remove duplicates) */
int create_notification_list_from_service(service *,int,int *);    		/* given a service, create list of contacts to be notified (remove duplicates) */
int add_notification(contact *);						/* adds a notification instance */
notification *find_notification(contact *);					/* finds a notification object */
time_t get_next_host_notification_time(host *,time_t);				/* calculates nex acceptable re-notification time for a host */
time_t get_next_service_notification_time(service *,time_t);			/* calculates nex acceptable re-notification time for a service */


/**** Logging Functions ****/
void logit(int,int,const char *, ...)
	__attribute__((__format__(__printf__, 3, 4)));
int write_to_logs_and_console(char *,unsigned long,int);	/* writes a string to screen and logs */
int write_to_console(char *);                           /* writes a string to screen */
int write_to_all_logs(char *,unsigned long);            /* writes a string to main log file and syslog facility */
int write_to_all_logs_with_timestamp(char *,unsigned long,time_t *);	/* writes a string to main log file and syslog facility */
int write_to_log(char *,unsigned long,time_t *);       	/* write a string to the main log file */
int write_to_syslog(char *,unsigned long);             	/* write a string to the syslog facility */
int log_service_event(service *);			/* logs a service event */
int log_host_event(host *);				/* logs a host event */
int log_host_states(int,time_t *);	                /* logs initial/current host states */
int log_service_states(int,time_t *);                   /* logs initial/current service states */
int rotate_log_file(time_t);			     	/* rotates the main log file */
int write_log_file_info(time_t *); 			/* records log file/version info */
int open_debug_log(void);
int log_debug_info(int,int,const char *,...)
	__attribute__((__format__(__printf__, 3, 4)));
int close_debug_log(void);


/**** Cleanup Functions ****/
void cleanup(void);                                  	/* cleanup after ourselves (before quitting or restarting) */
void free_memory(void);                              	/* free memory allocated to all linked lists in memory */
int reset_variables(void);                           	/* reset all global variables */
void free_notification_list(void);		     	/* frees all memory allocated to the notification list */


/**** Hash Functions ****/
int hashfunc(const char *name1, const char *name2, int hashslots);
int compare_hashdata(const char *,const char *,const char *,const char *);


/**** Miscellaneous Functions ****/
void sighandler(int);                                	/* handles signals */
void service_check_sighandler(int);                     /* handles timeouts when executing service checks */
void host_check_sighandler(int);                        /* handles timeouts when executing host checks */
void my_system_sighandler(int);				/* handles timeouts when executing commands via my_system() */
void file_lock_sighandler(int);				/* handles timeouts while waiting for file locks */
void strip(char *);                                  	/* strips whitespace from string */  
char *my_strtok(char *,char *);                      	/* my replacement for strtok() function (doesn't skip consecutive tokens) */
char *my_strsep(char **,const char *);		     	/* Solaris doesn't have strsep(), so I took this from the glibc source code */
#ifdef REMOVED_10182007
int my_free(void **);                                   /* my wrapper for free() */
#endif
char *get_next_string_from_buf(char *buf, int *start_index, int bufsize);
int compare_strings(char *,char *);                     /* compares two strings for equality */
char *escape_newlines(char *);
int contains_illegal_object_chars(char *);		/* tests whether or not an object name (host, service, etc.) contains illegal characters */
int my_rename(char *,char *);                           /* renames a file - works across filesystems */
int my_fcopy(char *,char *);                            /* copies a file - works across filesystems */
int get_raw_command_line(command *,char *,char **,int);    	/* given a raw command line, determine the actual command to run */
int check_time_against_period(time_t,timeperiod *);	/* check to see if a specific time is covered by a time period */
int is_daterange_single_day(daterange *);
time_t calculate_time_from_weekday_of_month(int,int,int,int);	/* calculates midnight time of specific (3rd, last, etc.) weekday of a particular month */
time_t calculate_time_from_day_of_month(int,int,int);	/* calculates midnight time of specific (1st, last, etc.) day of a particular month */
void get_next_valid_time(time_t, time_t *,timeperiod *);	/* get the next valid time in a time period */
void get_datetime_string(time_t *,char *,int,int);	/* get a date/time string for use in output */
void get_time_breakdown(unsigned long,int *,int *,int *, int *);
time_t get_next_log_rotation_time(void);	     	/* determine the next time to schedule a log rotation */
int init_embedded_perl(char **);			/* initialized embedded perl interpreter */
int deinit_embedded_perl(void);				/* cleans up embedded perl */
int file_uses_embedded_perl(char *);			/* tests whether or not the embedded perl interpreter should be used on a file */
int dbuf_init(dbuf *,int);
int dbuf_free(dbuf *);
int dbuf_strcat(dbuf *,char *);
int set_environment_var(char *,char *,int);             /* sets/clears and environment variable */
int check_for_nagios_updates(int,int);                  /* checks to see if new version of Nagios are available */
int query_update_api(void);                             /* checks to see if new version of Nagios are available */


/**** External Command Functions ****/
int check_for_external_commands(void);			/* checks for any external commands */
int process_external_command1(char *);                  /* top-level external command processor */
int process_external_command2(int,time_t,char *);	/* process an external command */
int process_external_commands_from_file(char *,int);    /* process external commands in a file */
int process_host_command(int,time_t,char *);            /* process an external host command */
int process_hostgroup_command(int,time_t,char *);       /* process an external hostgroup command */
int process_service_command(int,time_t,char *);         /* process an external service command */
int process_servicegroup_command(int,time_t,char *);    /* process an external servicegroup command */
int process_contact_command(int,time_t,char *);         /* process an external contact command */
int process_contactgroup_command(int,time_t,char *);    /* process an external contactgroup command */


/**** External Command Implementations ****/
int cmd_add_comment(int,time_t,char *);				/* add a service or host comment */
int cmd_delete_comment(int,char *);				/* delete a service or host comment */
int cmd_delete_all_comments(int,char *);			/* delete all comments associated with a host or service */
int cmd_delay_notification(int,char *);				/* delay a service or host notification */
int cmd_schedule_service_check(int,char *,int);			/* schedule an immediate or delayed service check */
int cmd_schedule_check(int,char *);				/* schedule an immediate or delayed host check */
int cmd_schedule_host_service_checks(int,char *,int);		/* schedule an immediate or delayed checks of all services on a host */
int cmd_signal_process(int,char *);				/* schedules a program shutdown or restart */
int cmd_process_service_check_result(int,time_t,char *);	/* processes a passive service check */
int cmd_process_host_check_result(int,time_t,char *);		/* processes a passive host check */
int cmd_acknowledge_problem(int,char *);			/* acknowledges a host or service problem */
int cmd_remove_acknowledgement(int,char *);			/* removes a host or service acknowledgement */
int cmd_schedule_downtime(int,time_t,char *);                   /* schedules host or service downtime */
int cmd_delete_downtime(int,char *);				/* cancels active/pending host or service scheduled downtime */
int cmd_change_object_int_var(int,char *);                      /* changes host/svc (int) variable */
int cmd_change_object_char_var(int,char *);			/* changes host/svc (char) variable */
int cmd_change_object_custom_var(int,char *);                   /* changes host/svc custom variable */
int cmd_process_external_commands_from_file(int,char *);        /* process external commands from a file */

int process_passive_service_check(time_t,char *,char *,int,char *);
int process_passive_host_check(time_t,char *,int,char *);


/**** Internal Command Implementations ****/
void disable_service_checks(service *);			/* disables a service check */
void enable_service_checks(service *);			/* enables a service check */
void schedule_service_check(service *,time_t,int);	/* schedules an immediate or delayed service check */
void schedule_host_check(host *,time_t,int);		/* schedules an immediate or delayed host check */
void enable_all_notifications(void);                    /* enables notifications on a program-wide basis */
void disable_all_notifications(void);                   /* disables notifications on a program-wide basis */
void enable_service_notifications(service *);		/* enables service notifications */
void disable_service_notifications(service *);		/* disables service notifications */
void enable_host_notifications(host *);			/* enables host notifications */
void disable_host_notifications(host *);		/* disables host notifications */
void enable_and_propagate_notifications(host *,int,int,int,int);	/* enables notifications for all hosts and services beyond a given host */
void disable_and_propagate_notifications(host *,int,int,int,int);	/* disables notifications for all hosts and services beyond a given host */
void schedule_and_propagate_downtime(host *,time_t,char *,char *,time_t,time_t,int,unsigned long,unsigned long); /* schedules downtime for all hosts beyond a given host */
void acknowledge_host_problem(host *,char *,char *,int,int,int);	/* acknowledges a host problem */
void acknowledge_service_problem(service *,char *,char *,int,int,int);	/* acknowledges a service problem */
void remove_host_acknowledgement(host *);		/* removes a host acknowledgement */
void remove_service_acknowledgement(service *);		/* removes a service acknowledgement */
void start_executing_service_checks(void);		/* starts executing service checks */
void stop_executing_service_checks(void);		/* stops executing service checks */
void start_accepting_passive_service_checks(void);	/* starts accepting passive service check results */
void stop_accepting_passive_service_checks(void);	/* stops accepting passive service check results */
void enable_passive_service_checks(service *);	        /* enables passive service checks for a particular service */
void disable_passive_service_checks(service *);         /* disables passive service checks for a particular service */
void start_using_event_handlers(void);			/* enables event handlers on a program-wide basis */
void stop_using_event_handlers(void);			/* disables event handlers on a program-wide basis */
void enable_service_event_handler(service *);		/* enables the event handler for a particular service */
void disable_service_event_handler(service *);		/* disables the event handler for a particular service */
void enable_host_event_handler(host *);			/* enables the event handler for a particular host */
void disable_host_event_handler(host *);		/* disables the event handler for a particular host */
void enable_host_checks(host *);			/* enables checks of a particular host */
void disable_host_checks(host *);			/* disables checks of a particular host */
void start_obsessing_over_service_checks(void);		/* start obsessing about service check results */
void stop_obsessing_over_service_checks(void);		/* stop obsessing about service check results */
void start_obsessing_over_host_checks(void);		/* start obsessing about host check results */
void stop_obsessing_over_host_checks(void);		/* stop obsessing about host check results */
void enable_service_freshness_checks(void);		/* enable service freshness checks */
void disable_service_freshness_checks(void);		/* disable service freshness checks */
void enable_host_freshness_checks(void);		/* enable host freshness checks */
void disable_host_freshness_checks(void);		/* disable host freshness checks */
void process_passive_checks(void);                      /* processes passive host and service check results */
void enable_all_failure_prediction(void);               /* enables failure prediction on a program-wide basis */
void disable_all_failure_prediction(void);              /* disables failure prediction on a program-wide basis */
void enable_performance_data(void);                     /* enables processing of performance data on a program-wide basis */
void disable_performance_data(void);                    /* disables processing of performance data on a program-wide basis */
void start_executing_host_checks(void);			/* starts executing host checks */
void stop_executing_host_checks(void);			/* stops executing host checks */
void start_accepting_passive_host_checks(void);		/* starts accepting passive host check results */
void stop_accepting_passive_host_checks(void);		/* stops accepting passive host check results */
void enable_passive_host_checks(host *);	        /* enables passive host checks for a particular host */
void disable_passive_host_checks(host *);         	/* disables passive host checks for a particular host */
void start_obsessing_over_service(service *);		/* start obsessing about specific service check results */
void stop_obsessing_over_service(service *);		/* stop obsessing about specific service check results */
void start_obsessing_over_host(host *);			/* start obsessing about specific host check results */
void stop_obsessing_over_host(host *);			/* stop obsessing about specific host check results */
void set_host_notification_number(host *,int);		/* sets current notification number for a specific host */
void set_service_notification_number(service *,int);	/* sets current notification number for a specific service */
void enable_contact_host_notifications(contact *);      /* enables host notifications for a specific contact */
void disable_contact_host_notifications(contact *);     /* disables host notifications for a specific contact */
void enable_contact_service_notifications(contact *);   /* enables service notifications for a specific contact */
void disable_contact_service_notifications(contact *);  /* disables service notifications for a specific contact */

int init_check_result_worker_thread(void);
int shutdown_check_result_worker_thread(void);
void * check_result_worker_thread(void *);
void cleanup_check_result_worker_thread(void *);

int init_command_file_worker_thread(void);
int shutdown_command_file_worker_thread(void);
void * command_file_worker_thread(void *);
void cleanup_command_file_worker_thread(void *);

int submit_external_command(char *,int *);
int submit_raw_external_command(char *,time_t *,int *);

char *get_program_version(void);
char *get_program_modification_date(void);

mmapfile *mmap_fopen(char *);				/* open a file read-only via mmap() */
int mmap_fclose(mmapfile *);
char *mmap_fgets(mmapfile *);
char *mmap_fgets_multiline(mmapfile *);


#ifdef __cplusplus
}
#endif
#endif

