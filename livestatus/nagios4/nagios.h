/************************************************************************
 *
 * Nagios Main Header File
 * Written By: Ethan Galstad (egalstad@nagios.org)
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

#ifndef NSCORE
# define NSCORE
#endif

#include "defaults.h"
#include "common.h"
#include "logging.h"
#include "locations.h"
#include "objects.h"
#include "macros.h"
#include "config.h"

NAGIOS_BEGIN_DECL

/*
 * global variables only used in the core. Reducing this list would be
 * a Good Thing(tm).
 */
extern char *nagios_binary_path;
extern char *config_file;
extern char *command_file;
extern char *temp_file;
extern char *temp_path;
extern char *check_result_path;
extern char *lock_file;
extern char *object_precache_file;

extern unsigned int nofile_limit, nproc_limit, max_apps;

extern int num_check_workers;
extern char *qh_socket_path;

extern char *nagios_user;
extern char *nagios_group;

extern char *macro_user[MAX_USER_MACROS];

extern char *ocsp_command;
extern char *ochp_command;
extern command *ocsp_command_ptr;
extern command *ochp_command_ptr;
extern int ocsp_timeout;
extern int ochp_timeout;

extern char *global_host_event_handler;
extern char *global_service_event_handler;
extern command *global_host_event_handler_ptr;
extern command *global_service_event_handler_ptr;

extern char *illegal_object_chars;

extern int use_regexp_matches;
extern int use_true_regexp_matching;

extern int use_syslog;
extern char *log_file;
extern char *log_archive_path;
extern int log_notifications;
extern int log_service_retries;
extern int log_host_retries;
extern int log_event_handlers;
extern int log_external_commands;
extern int log_passive_checks;
extern unsigned long logging_options;
extern unsigned long syslog_options;

extern int service_check_timeout;
extern int service_check_timeout_state;
extern int host_check_timeout;
extern int event_handler_timeout;
extern int notification_timeout;

extern int log_initial_states;
extern int log_current_states;

extern int daemon_dumps_core;
extern int sig_id;
extern int caught_signal;


extern int verify_config;
extern int test_scheduling;
extern int precache_objects;
extern int use_precached_objects;

extern int service_inter_check_delay_method;
extern int host_inter_check_delay_method;
extern int service_interleave_factor_method;
extern int max_host_check_spread;
extern int max_service_check_spread;

extern sched_info scheduling_info;

extern int max_parallel_service_checks;

extern int check_reaper_interval;
extern int max_check_reaper_time;
extern int service_freshness_check_interval;
extern int host_freshness_check_interval;
extern int auto_rescheduling_interval;
extern int auto_rescheduling_window;

extern int check_orphaned_services;
extern int check_orphaned_hosts;
extern int check_service_freshness;
extern int check_host_freshness;
extern int auto_reschedule_checks;

extern int additional_freshness_latency;

extern int check_for_updates;
extern int bare_update_check;
extern time_t last_update_check;
extern unsigned long update_uid;
extern int update_available;
extern char *last_program_version;
extern char *new_program_version;

extern int use_aggressive_host_checking;
extern time_t cached_host_check_horizon;
extern time_t cached_service_check_horizon;
extern int enable_predictive_host_dependency_checks;
extern int enable_predictive_service_dependency_checks;

extern int soft_state_dependencies;

extern int retain_state_information;
extern int retention_update_interval;
extern int use_retained_program_state;
extern int use_retained_scheduling_info;
extern int retention_scheduling_horizon;
extern char *retention_file;
extern unsigned long retained_host_attribute_mask;
extern unsigned long retained_service_attribute_mask;
extern unsigned long retained_contact_host_attribute_mask;
extern unsigned long retained_contact_service_attribute_mask;
extern unsigned long retained_process_host_attribute_mask;
extern unsigned long retained_process_service_attribute_mask;

extern int translate_passive_host_checks;
extern int passive_host_checks_are_soft;

extern int status_update_interval;
extern char *retention_file;

extern int time_change_threshold;

extern unsigned long event_broker_options;

extern double low_service_flap_threshold;
extern double high_service_flap_threshold;
extern double low_host_flap_threshold;
extern double high_host_flap_threshold;

extern int use_large_installation_tweaks;
extern int enable_environment_macros;
extern int free_child_process_memory;
extern int child_processes_fork_twice;

extern char *use_timezone;

extern time_t max_check_result_file_age;

extern char *debug_file;
extern int debug_level;
extern int debug_verbosity;
extern unsigned long max_debug_file_size;

extern int allow_empty_hostgroup_assignment;

extern time_t last_program_stop;
extern time_t event_start;

extern int sigshutdown, sigrestart;
extern int currently_running_service_checks;
extern int currently_running_host_checks;

extern unsigned long next_event_id;
extern unsigned long next_problem_id;
extern unsigned long next_comment_id;
extern unsigned long next_notification_id;

extern unsigned long modified_process_attributes;
extern unsigned long modified_host_process_attributes;
extern unsigned long modified_service_process_attributes;

extern squeue_t *nagios_squeue;
extern iobroker_set *nagios_iobs;

extern struct check_stats check_statistics[MAX_CHECK_STATS_TYPES];

/*** perfdata variables ***/
extern int     perfdata_timeout;
extern char    *host_perfdata_command;
extern char    *service_perfdata_command;
extern char    *host_perfdata_file_template;
extern char    *service_perfdata_file_template;
extern char    *host_perfdata_file;
extern char    *service_perfdata_file;
extern int     host_perfdata_file_append;
extern int     service_perfdata_file_append;
extern int     host_perfdata_file_pipe;
extern int     service_perfdata_file_pipe;
extern unsigned long host_perfdata_file_processing_interval;
extern unsigned long service_perfdata_file_processing_interval;
extern char    *host_perfdata_file_processing_command;
extern char    *service_perfdata_file_processing_command;
extern int     host_perfdata_process_empty_results;
extern int     service_perfdata_process_empty_results;
/*** end perfdata variables */

extern struct notify_list *notification_list;

extern struct check_engine nagios_check_engine;

/*
 * Everything we need to keep system load in check.
 * Don't use this from modules.
 */
struct load_control {
	time_t last_check;  /* last time we checked the real load */
	time_t last_change; /* last time we changed settings */
	time_t check_interval; /* seconds between load checks */
	double load[3];      /* system load, as reported by getloadavg() */
	float backoff_limit; /* limit we must reach before we back off */
	float rampup_limit;  /* limit we must reach before we ramp back up */
	unsigned int backoff_change; /* backoff by this much */
	unsigned int rampup_change;  /* ramp up by this much */
	unsigned int changes;  /* number of times we've changed settings */
	unsigned int jobs_max;   /* upper setting for jobs_limit */
	unsigned int jobs_limit; /* current limit */
	unsigned int jobs_min;   /* lower setting for jobs_limit */
	unsigned int jobs_running;  /* jobs currently running */
	unsigned int nproc_limit;  /* rlimit for user processes */
	unsigned int nofile_limit; /* rlimit for open files */
	unsigned int options; /* various option flags */
};
extern struct load_control loadctl;

/* options for load control */
#define LOADCTL_ENABLED    (1 << 0)


	/************* MISC LENGTH/SIZE DEFINITIONS ***********/

	/*
	   NOTE: Plugin length is artificially capped at 8k to prevent runaway plugins from returning MBs/GBs of data
	   back to Nagios.  If you increase the 8k cap by modifying this value, make sure you also increase the value
	   of MAX_EXTERNAL_COMMAND_LENGTH in common.h to allow for passive checks results received through the external
	   command file. EG 10/19/07
	*/
#define MAX_PLUGIN_OUTPUT_LENGTH                8192    /* max length of plugin output (including perf data) */


	/******************* STATE LOGGING TYPES **************/

#define INITIAL_STATES                  1
#define CURRENT_STATES                  2



	/************ SERVICE DEPENDENCY VALUES ***************/

#define DEPENDENCIES_OK			0
#define DEPENDENCIES_FAILED		1



	/*********** ROUTE CHECK PROPAGATION TYPES ************/

#define PROPAGATE_TO_PARENT_HOSTS	1
#define PROPAGATE_TO_CHILD_HOSTS	2



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
#define NOTIFICATION_CUSTOM             8



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

/*
 * VERSIONFIX: Make EVENT_SLEEP and EVENT_USER_FUNCTION appear
 * linearly in order.
 */

#define EVENT_TYPE_STR(type)	( \
	type == EVENT_SERVICE_CHECK ? "SERVICE_CHECK" : \
	type == EVENT_COMMAND_CHECK ? "COMMAND_CHECK" : \
	type == EVENT_LOG_ROTATION ? "LOG_ROTATION" : \
	type == EVENT_PROGRAM_SHUTDOWN ? "PROGRAM_SHUTDOWN" : \
	type == EVENT_PROGRAM_RESTART ? "PROGRAM_RESTART" : \
	type == EVENT_CHECK_REAPER ? "CHECK_REAPER" : \
	type == EVENT_ORPHAN_CHECK ? "ORPHAN_CHECK" : \
	type == EVENT_RETENTION_SAVE ? "RETENTION_SAVE" : \
	type == EVENT_STATUS_SAVE ? "STATUS_SAVE" : \
	type == EVENT_SCHEDULED_DOWNTIME ? "SCHEDULED_DOWNTIME" : \
	type == EVENT_SFRESHNESS_CHECK ? "SFRESHNESS_CHECK" : \
	type == EVENT_EXPIRE_DOWNTIME ? "EXPIRE_DOWNTIME" : \
	type == EVENT_HOST_CHECK ? "HOST_CHECK" : \
	type == EVENT_HFRESHNESS_CHECK ? "HFRESHNESS_CHECK" : \
	type == EVENT_RESCHEDULE_CHECKS ? "RESCHEDULE_CHECKS" : \
	type == EVENT_EXPIRE_COMMENT ? "EXPIRE_COMMENT" : \
	type == EVENT_CHECK_PROGRAM_UPDATE ? "CHECK_PROGRAM_UPDATE" : \
	type == EVENT_SLEEP ? "SLEEP" : \
	type == EVENT_USER_FUNCTION ? "USER_FUNCTION" : \
	"UNKNOWN" \
)



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


/* useful for hosts and services to determine time 'til next check */
#define normal_check_window(o) ((time_t)(o->check_interval * interval_length))
#define retry_check_window(o) ((time_t)(o->retry_interval * interval_length))
#define check_window(o) \
	((!o->current_state && o->state_type == SOFT_STATE) ? \
		retry_check_window(o) : \
		normal_check_window(o))

/** Nerd subscription type */
struct nerd_subscription {
	int sd;
	struct nerd_channel *chan;
	char *format; /* requested format (macro string) for this subscription */
};

/******************** FUNCTIONS **********************/
extern int set_loadctl_options(char *opts, unsigned int len);

/* silly helpers useful pretty much all over the place */
extern const char *service_state_name(int state);
extern const char *host_state_name(int state);
extern const char *state_type_name(int state_type);
extern const char *check_type_name(int check_type);
extern const char *check_result_source(check_result *cr);

/*** Nagios Event Radio Dispatcher functions ***/
extern int nerd_init(void);
extern int nerd_mkchan(const char *name, const char *description, int (*handler)(int, void *), unsigned int callbacks);
extern int nerd_cancel_subscriber(int sd);
extern int nerd_get_channel_id(const char *chan_name);
extern objectlist *nerd_get_subscriptions(int chan_id);
extern int nerd_broadcast(unsigned int chan_id, void *buf, unsigned int len);

/*** Query Handler functions, types and macros*/
typedef int (*qh_handler)(int, char *, unsigned int);
extern int dump_event_stats(int sd);

/* return codes for query_handlers() */
#define QH_OK        0  /* keep listening */
#define QH_CLOSE     1  /* we should close the socket */
#define QH_INVALID   2  /* invalid query. Log and close */
#define QH_TAKEOVER  3  /* handler will take full control. de-register but don't close */
extern int qh_init(const char *path);
extern void qh_deinit(const char *path);
extern int qh_register_handler(const char *name, const char *description, unsigned int options, qh_handler handler);
extern const char *qh_strerror(int code);

/**** Configuration Functions ****/
int read_main_config_file(char *);                     		/* reads the main config file (nagios.cfg) */
int read_resource_file(char *);					/* processes macros in resource file */
int read_all_object_data(char *);				/* reads all object config data */


/**** Setup Functions ****/
int pre_flight_check(void);                          		/* try and verify the configuration data */
int pre_flight_object_check(int *, int *);               	/* verify object relationships and settings */
int pre_flight_circular_check(int *, int *);             	/* detects circular dependencies and paths */
void init_timing_loop(void);                         		/* setup the initial scheduling queue */
void setup_sighandler(void);                         		/* trap signals */
void reset_sighandler(void);                         		/* reset signals to default action */
extern void handle_sigxfsz(int);				/* handle SIGXFSZ */

int daemon_init(void);				     		/* switches to daemon mode */
int drop_privileges(char *, char *);				/* drops privileges before startup */
void display_scheduling_info(void);				/* displays service check scheduling information */


/**** Event Queue Functions ****/
int init_event_queue(void); /* creates the queue nagios_squeue */
timed_event *schedule_new_event(int, int, time_t, int, unsigned long, void *, int, void *, void *, int);	/* schedules a new timed event */
void reschedule_event(squeue_t *sq, timed_event *event);   		/* reschedules an event */
void add_event(squeue_t *sq, timed_event *event);     		/* adds an event to the execution queue */
void remove_event(squeue_t *sq, timed_event *event);     		/* remove an event from the execution queue */
int event_execution_loop(void);                      		/* main monitoring/event handler loop */
int handle_timed_event(timed_event *);		     		/* top level handler for timed events */
void adjust_check_scheduling(void);		        	/* auto-adjusts scheduling of host and service checks */
void compensate_for_system_time_change(unsigned long, unsigned long);	/* attempts to compensate for a change in the system time */
void adjust_timestamp_for_time_change(time_t, time_t, unsigned long, time_t *); /* adjusts a timestamp variable for a system time change */


/**** IPC Functions ****/
int process_check_result_queue(char *);
int process_check_result_file(char *);
int process_check_result(check_result *);
int delete_check_result_file(char *);
int init_check_result(check_result *);
int free_check_result(check_result *);                  	/* frees memory associated with a host/service check result */
int parse_check_output(char *, char **, char **, char **, int, int);
int open_command_file(void);					/* creates the external command file as a named pipe (FIFO) and opens it for reading */
int close_command_file(void);					/* closes and deletes the external command file (FIFO) */


/**** Monitoring/Event Handler Functions ****/
int check_service_dependencies(service *, int);          	/* checks service dependencies */
int check_host_dependencies(host *, int);                	/* checks host dependencies */
void check_for_orphaned_services(void);				/* checks for orphaned services */
void check_for_orphaned_hosts(void);				/* checks for orphaned hosts */
void check_service_result_freshness(void);              	/* checks the "freshness" of service check results */
int is_service_result_fresh(service *, time_t, int);            /* determines if a service's check results are fresh */
void check_host_result_freshness(void);                 	/* checks the "freshness" of host check results */
int is_host_result_fresh(host *, time_t, int);                  /* determines if a host's check results are fresh */
int my_system(char *, int, int *, double *, char **, int);         	/* executes a command via popen(), but also protects against timeouts */
int my_system_r(nagios_macros *mac, char *, int, int *, double *, char **, int); /* thread-safe version of the above */


/**** Flap Detection Functions ****/
void check_for_service_flapping(service *, int, int);	      /* determines whether or not a service is "flapping" between states */
void check_for_host_flapping(host *, int, int, int);		/* determines whether or not a host is "flapping" between states */
void set_service_flap(service *, double, double, double, int);	/* handles a service that is flapping */
void clear_service_flap(service *, double, double, double);	/* handles a service that has stopped flapping */
void set_host_flap(host *, double, double, double, int);		/* handles a host that is flapping */
void clear_host_flap(host *, double, double, double);		/* handles a host that has stopped flapping */
void enable_flap_detection_routines(void);			/* enables flap detection on a program-wide basis */
void disable_flap_detection_routines(void);			/* disables flap detection on a program-wide basis */
void enable_host_flap_detection(host *);			/* enables flap detection for a particular host */
void disable_host_flap_detection(host *);			/* disables flap detection for a particular host */
void enable_service_flap_detection(service *);			/* enables flap detection for a particular service */
void disable_service_flap_detection(service *);			/* disables flap detection for a particular service */
void handle_host_flap_detection_disabled(host *);		/* handles the details when flap detection is disabled globally or on a per-host basis */
void handle_service_flap_detection_disabled(service *);		/* handles the details when flap detection is disabled globally or on a per-service basis */


/**** Route/Host Check Functions ****/
int check_host_check_viability(host *, int, int *, time_t *);
int adjust_host_check_attempt(host *, int);
int determine_host_reachability(host *);
int process_host_check_result(host *, int, char *, int, int, int, unsigned long);
int perform_on_demand_host_check(host *, int *, int, int, unsigned long);
int execute_sync_host_check(host *);
int run_scheduled_host_check(host *, int, double);
int run_async_host_check(host *, int, double, int, int, int *, time_t *);
int handle_async_host_check_result(host *, check_result *);


/**** Service Check Functions ****/
int check_service_check_viability(service *, int, int *, time_t *);
int run_scheduled_service_check(service *, int, double);
int run_async_service_check(service *, int, double, int, int, int *, time_t *);
int handle_async_service_check_result(service *, check_result *);


/**** Event Handler Functions ****/
int handle_host_state(host *);               			/* top level host state handler */


/**** Common Check Fucntions *****/
int reap_check_results(void);


/**** Check Statistics Functions ****/
int init_check_stats(void);
int update_check_stats(int, time_t);
int generate_check_stats(void);


/**** Event Handler Functions ****/
int obsessive_compulsive_service_check_processor(service *);	/* distributed monitoring craziness... */
int obsessive_compulsive_host_check_processor(host *);		/* distributed monitoring craziness... */
int handle_service_event(service *);				/* top level service event logic */
int run_service_event_handler(nagios_macros *mac, service *);			/* runs the event handler for a specific service */
int run_global_service_event_handler(nagios_macros *mac, service *);		/* runs the global service event handler */
int handle_host_event(host *);					/* top level host event logic */
int run_host_event_handler(nagios_macros *mac, host *);				/* runs the event handler for a specific host */
int run_global_host_event_handler(nagios_macros *mac, host *);			/* runs the global host event handler */


/**** Notification Functions ****/
const char *notification_reason_name(unsigned int reason_type);
int check_service_notification_viability(service *, int, int);			/* checks viability of notifying all contacts about a service */
int is_valid_escalation_for_service_notification(service *, serviceescalation *, int);	/* checks if an escalation entry is valid for a particular service notification */
int should_service_notification_be_escalated(service *);			/* checks if a service notification should be escalated */
int service_notification(service *, int, char *, char *, int);                     	/* notify all contacts about a service (problem or recovery) */
int check_contact_service_notification_viability(contact *, service *, int, int);	/* checks viability of notifying a contact about a service */
int notify_contact_of_service(nagios_macros *mac, contact *, service *, int, char *, char *, int, int);  	/* notify a single contact about a service */
int check_host_notification_viability(host *, int, int);				/* checks viability of notifying all contacts about a host */
int is_valid_escalation_for_host_notification(host *, hostescalation *, int);	/* checks if an escalation entry is valid for a particular host notification */
int should_host_notification_be_escalated(host *);				/* checks if a host notification should be escalated */
int host_notification(host *, int, char *, char *, int);                           	/* notify all contacts about a host (problem or recovery) */
int check_contact_host_notification_viability(contact *, host *, int, int);	/* checks viability of notifying a contact about a host */
int notify_contact_of_host(nagios_macros *mac, contact *, host *, int, char *, char *, int, int);        	/* notify a single contact about a host */
int create_notification_list_from_host(nagios_macros *mac, host *,int,int *,int);         		/* given a host, create list of contacts to be notified (remove duplicates) */
int create_notification_list_from_service(nagios_macros *mac, service *,int,int *,int);    		/* given a service, create list of contacts to be notified (remove duplicates) */
int add_notification(nagios_macros *mac, contact *);						/* adds a notification instance */
notification *find_notification(contact *);					/* finds a notification object */
time_t get_next_host_notification_time(host *, time_t);				/* calculates nex acceptable re-notification time for a host */
time_t get_next_service_notification_time(service *, time_t);			/* calculates nex acceptable re-notification time for a service */


/**** Cleanup Functions ****/
void cleanup(void);                                  	/* cleanup after ourselves (before quitting or restarting) */
void free_memory(nagios_macros *mac);                              	/* free memory allocated to all linked lists in memory */
int reset_variables(void);                           	/* reset all global variables */
void free_notification_list(void);		     	/* frees all memory allocated to the notification list */


/**** Miscellaneous Functions ****/
void sighandler(int);                                	/* handles signals */
void my_system_sighandler(int);				/* handles timeouts when executing commands via my_system() */
char *get_next_string_from_buf(char *buf, int *start_index, int bufsize);
int compare_strings(char *, char *);                    /* compares two strings for equality */
char *escape_newlines(char *);
int contains_illegal_object_chars(char *);		/* tests whether or not an object name (host, service, etc.) contains illegal characters */
int my_rename(char *, char *);                          /* renames a file - works across filesystems */
int my_fcopy(char *, char *);                           /* copies a file - works across filesystems */
int my_fdcopy(char *, char *, int);                     /* copies a named source to an already opened destination file */

/* thread-safe version of get_raw_command_line_r() */
extern int get_raw_command_line_r(nagios_macros *mac, command *, char *, char **, int);

/*
 * given a raw command line, determine the actual command to run
 * Manipulates global_macros.argv and is thus not threadsafe
 */
extern int get_raw_command_line(command *, char *, char **, int);

int check_time_against_period(time_t, timeperiod *);	/* check to see if a specific time is covered by a time period */
int is_daterange_single_day(daterange *);
time_t calculate_time_from_weekday_of_month(int, int, int, int);	/* calculates midnight time of specific (3rd, last, etc.) weekday of a particular month */
time_t calculate_time_from_day_of_month(int, int, int);	/* calculates midnight time of specific (1st, last, etc.) day of a particular month */
void get_next_valid_time(time_t, time_t *, timeperiod *);	/* get the next valid time in a time period */
time_t get_next_log_rotation_time(void);	     	/* determine the next time to schedule a log rotation */
int dbuf_init(dbuf *, int);
int dbuf_free(dbuf *);
int dbuf_strcat(dbuf *, const char *);
int set_environment_var(char *, char *, int);           /* sets/clears and environment variable */
int check_for_nagios_updates(int, int);                 /* checks to see if new version of Nagios are available */
int query_update_api(void);                             /* checks to see if new version of Nagios are available */


/**** External Command Functions ****/
int process_external_command1(char *);                  /* top-level external command processor */
int process_external_command2(int, time_t, char *);	/* process an external command */
int process_external_commands_from_file(char *, int);   /* process external commands in a file */
int process_host_command(int, time_t, char *);          /* process an external host command */
int process_hostgroup_command(int, time_t, char *);     /* process an external hostgroup command */
int process_service_command(int, time_t, char *);       /* process an external service command */
int process_servicegroup_command(int, time_t, char *);  /* process an external servicegroup command */
int process_contact_command(int, time_t, char *);       /* process an external contact command */
int process_contactgroup_command(int, time_t, char *);  /* process an external contactgroup command */


/**** External Command Implementations ****/
int cmd_add_comment(int, time_t, char *);				/* add a service or host comment */
int cmd_delete_comment(int, char *);				/* delete a service or host comment */
int cmd_delete_all_comments(int, char *);			/* delete all comments associated with a host or service */
int cmd_delay_notification(int, char *);				/* delay a service or host notification */
int cmd_schedule_check(int, char *);				/* schedule an immediate or delayed host check */
int cmd_schedule_host_service_checks(int, char *, int);		/* schedule an immediate or delayed checks of all services on a host */
int cmd_signal_process(int, char *);				/* schedules a program shutdown or restart */
int cmd_process_service_check_result(int, time_t, char *);	/* processes a passive service check */
int cmd_process_host_check_result(int, time_t, char *);		/* processes a passive host check */
int cmd_acknowledge_problem(int, char *);			/* acknowledges a host or service problem */
int cmd_remove_acknowledgement(int, char *);			/* removes a host or service acknowledgement */
int cmd_schedule_downtime(int, time_t, char *);                 /* schedules host or service downtime */
int cmd_delete_downtime(int, char *);				/* cancels active/pending host or service scheduled downtime */
int cmd_change_object_int_var(int, char *);                     /* changes host/svc (int) variable */
int cmd_change_object_char_var(int, char *);			/* changes host/svc (char) variable */
int cmd_change_object_custom_var(int, char *);                  /* changes host/svc custom variable */
int cmd_process_external_commands_from_file(int, char *);       /* process external commands from a file */
int cmd_delete_downtime_by_start_time_comment(int, char *);
int cmd_delete_downtime_by_host_name(int, char *);
int cmd_delete_downtime_by_hostgroup_name(int, char *);

int process_passive_service_check(time_t, char *, char *, int, char *);
int process_passive_host_check(time_t, char *, int, char *);


/**** Internal Command Implementations ****/
void disable_service_checks(service *);			/* disables a service check */
void enable_service_checks(service *);			/* enables a service check */
void schedule_service_check(service *, time_t, int);	/* schedules an immediate or delayed service check */
void schedule_host_check(host *, time_t, int);		/* schedules an immediate or delayed host check */
void enable_all_notifications(void);                    /* enables notifications on a program-wide basis */
void disable_all_notifications(void);                   /* disables notifications on a program-wide basis */
void enable_service_notifications(service *);		/* enables service notifications */
void disable_service_notifications(service *);		/* disables service notifications */
void enable_host_notifications(host *);			/* enables host notifications */
void disable_host_notifications(host *);		/* disables host notifications */
void enable_and_propagate_notifications(host *, int, int, int, int);	/* enables notifications for all hosts and services beyond a given host */
void disable_and_propagate_notifications(host *, int, int, int, int);	/* disables notifications for all hosts and services beyond a given host */
void schedule_and_propagate_downtime(host *, time_t, char *, char *, time_t, time_t, int, unsigned long, unsigned long); /* schedules downtime for all hosts beyond a given host */
void acknowledge_host_problem(host *, char *, char *, int, int, int);	/* acknowledges a host problem */
void acknowledge_service_problem(service *, char *, char *, int, int, int);	/* acknowledges a service problem */
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
void set_host_notification_number(host *, int);		/* sets current notification number for a specific host */
void set_service_notification_number(service *, int);	/* sets current notification number for a specific service */
void enable_contact_host_notifications(contact *);      /* enables host notifications for a specific contact */
void disable_contact_host_notifications(contact *);     /* disables host notifications for a specific contact */
void enable_contact_service_notifications(contact *);   /* enables service notifications for a specific contact */
void disable_contact_service_notifications(contact *);  /* disables service notifications for a specific contact */

int launch_command_file_worker(void);
int shutdown_command_file_worker(void);

char *get_program_version(void);
char *get_program_modification_date(void);

NAGIOS_END_DECL
#endif

