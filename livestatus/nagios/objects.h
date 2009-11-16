
/*****************************************************************************
 *
 * OBJECTS.H - Header file for object addition/search functions
 *
 * Copyright (c) 1999-2007 Ethan Galstad (egalstad@nagios.org)
 * Last Modified: 11-10-2007
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
 *
 *****************************************************************************/


#ifndef _OBJECTS_H
#define _OBJECTS_H

#include "config.h"
#include "common.h"

#ifdef __cplusplus
  extern "C" {
#endif



/*************** CURRENT OBJECT REVISION **************/

#define CURRENT_OBJECT_STRUCTURE_VERSION        307     /* increment when changes are made to data structures... */
	                                                /* Nagios 3 starts at 300, Nagios 4 at 400, etc. */



/***************** OBJECT SIZE LIMITS *****************/

#define MAX_STATE_HISTORY_ENTRIES		21	/* max number of old states to keep track of for flap detection */
#define MAX_CONTACT_ADDRESSES                   6       /* max number of custom addresses a contact can have */



/***************** SKIP LISTS ****************/

#define NUM_OBJECT_SKIPLISTS                   12

#define HOST_SKIPLIST                          0
#define SERVICE_SKIPLIST                       1
#define COMMAND_SKIPLIST                       2
#define TIMEPERIOD_SKIPLIST                    3
#define CONTACT_SKIPLIST                       4
#define CONTACTGROUP_SKIPLIST                  5
#define HOSTGROUP_SKIPLIST                     6
#define SERVICEGROUP_SKIPLIST                  7
#define HOSTDEPENDENCY_SKIPLIST                8
#define SERVICEDEPENDENCY_SKIPLIST             9
#define HOSTESCALATION_SKIPLIST                10
#define SERVICEESCALATION_SKIPLIST             11


/****************** DATA STRUCTURES *******************/

typedef struct host_struct host;
typedef struct service_struct service;
typedef struct contact_struct contact;

/* OBJECT LIST STRUCTURE */
typedef struct objectlist_struct{
	void      *object_ptr;
	struct objectlist_struct *next;
        }objectlist;


/* TIMERANGE structure */
typedef struct timerange_struct{
	unsigned long range_start;
	unsigned long range_end;
	struct timerange_struct *next;
        }timerange;


/* DATERANGE structure */
typedef struct daterange_struct{
	int type;
	int syear;          /* start year */
	int smon;           /* start month */
	int smday;          /* start day of month (may 3rd, last day in feb) */
	int swday;          /* start day of week (thursday) */
	int swday_offset;   /* start weekday offset (3rd thursday, last monday in jan) */
	int eyear;
	int emon;
	int emday;
	int ewday;
	int ewday_offset;
	int skip_interval;
	timerange *times;
	struct daterange_struct *next;
	}daterange;


/* TIMEPERIODEXCLUSION structure */
typedef struct timeperiodexclusion_struct{
	char  *timeperiod_name;
	struct timeperiod_struct *timeperiod_ptr;
	struct timeperiodexclusion_struct *next;
        }timeperiodexclusion;


/* TIMEPERIOD structure */
typedef struct timeperiod_struct{
	char    *name;
	char    *alias;
	timerange *days[7];
	daterange *exceptions[DATERANGE_TYPES];
	timeperiodexclusion *exclusions;
	struct 	timeperiod_struct *next;
	struct 	timeperiod_struct *nexthash;
	}timeperiod;


/* CONTACTSMEMBER structure */
typedef struct contactsmember_struct{
	char    *contact_name;
#ifdef NSCORE
	contact *contact_ptr;
#endif
	struct  contactsmember_struct *next;
        }contactsmember;


/* CONTACTGROUP structure */
typedef struct contactgroup_struct{
	char	*group_name;
	char    *alias;
	contactsmember *members;
	struct	contactgroup_struct *next;
	struct	contactgroup_struct *nexthash;
	}contactgroup;


/* CONTACTGROUPSMEMBER structure */
typedef struct contactgroupsmember_struct{
	char    *group_name;
#ifdef NSCORE
	contactgroup *group_ptr;
#endif
	struct contactgroupsmember_struct *next;
        }contactgroupsmember;


/* CUSTOMVARIABLESMEMBER structure */
typedef struct customvariablesmember_struct{
	char    *variable_name;
	char    *variable_value;
	int     has_been_modified;
	struct customvariablesmember_struct *next;
        }customvariablesmember;


/* COMMAND structure */
typedef struct command_struct{
	char    *name;
	char    *command_line;
	struct command_struct *next;
	struct command_struct *nexthash;
        }command;


/* COMMANDSMEMBER structure */
typedef struct commandsmember_struct{
	char	*command_dummy;
#ifdef NSCORE
	command *command_ptr;
#endif
	struct	commandsmember_struct *next;
	}commandsmember;


/* CONTACT structure */
struct contact_struct{
	char	*name;
	char	*alias;
	char	*email;
	char	*pager;
	char    *address[MAX_CONTACT_ADDRESSES];
	commandsmember *host_notification_commands;
	commandsmember *service_notification_commands;	
	int     notify_on_service_unknown;
	int     notify_on_service_warning;
	int     notify_on_service_critical;
	int     notify_on_service_recovery;
	int     notify_on_service_flapping;
	int     notify_on_service_downtime;
	int 	notify_on_host_down;
	int	notify_on_host_unreachable;
	int	notify_on_host_recovery;
	int     notify_on_host_flapping;
	int     notify_on_host_downtime;
	char	*host_notification_period;
	char	*service_notification_period;
	int     host_notifications_enabled;
	int     service_notifications_enabled;
	int     can_submit_commands;
	int     retain_status_information;
	int     retain_nonstatus_information;
	customvariablesmember *custom_variables;
#ifdef NSCORE
	time_t  last_host_notification;
	time_t  last_service_notification;
	unsigned long modified_attributes;
	unsigned long modified_host_attributes;
	unsigned long modified_service_attributes;

	timeperiod *host_notification_period_ptr;
	timeperiod *service_notification_period_ptr;
	objectlist *contactgroups_ptr;
#endif
	struct	contact_struct *next;
	struct	contact_struct *nexthash;
        };


/* SERVICESMEMBER structure */
typedef struct servicesmember_struct{
	char    *host_name;
	char    *service_description;
#ifdef NSCORE
	service *service_ptr;
#endif
	struct servicesmember_struct *next;
        }servicesmember;


/* HOSTSMEMBER structure */
typedef struct hostsmember_struct{
	char    *host_name;
#ifdef NSCORE
	host    *host_ptr;
#endif
	struct hostsmember_struct *next;
        }hostsmember;


/* HOSTGROUP structure */
typedef struct hostgroup_struct{
	char 	*group_name;
	char    *alias;
	hostsmember *members;
	char    *notes;
	char    *notes_url;
	char    *action_url;
	struct	hostgroup_struct *next;
	struct	hostgroup_struct *nexthash;
	}hostgroup;


/* HOST structure */
struct host_struct{
	char    *name;
	char    *display_name;
	char	*alias;
	char    *address;
        hostsmember *parent_hosts;
        hostsmember *child_hosts;
	servicesmember *services;
	char    *host_check_command;
	int     initial_state;
	double  check_interval;
	double  retry_interval;
	int     max_attempts;
	char    *event_handler;
	contactgroupsmember *contact_groups;
	contactsmember *contacts;
	double  notification_interval;
	double  first_notification_delay;
	int	notify_on_down;
	int	notify_on_unreachable;
	int     notify_on_recovery;
	int     notify_on_flapping;
	int     notify_on_downtime;
	char	*notification_period;
	char    *check_period;
	int     flap_detection_enabled;
	double  low_flap_threshold;
	double  high_flap_threshold;
	int     flap_detection_on_up;
	int     flap_detection_on_down;
	int     flap_detection_on_unreachable;
	int     stalk_on_up;
	int     stalk_on_down;
	int     stalk_on_unreachable;
	int     check_freshness;
	int     freshness_threshold;
	int     process_performance_data;
	int     checks_enabled;
	int     accept_passive_host_checks;
	int     event_handler_enabled;
	int     retain_status_information;
	int     retain_nonstatus_information;
	int     failure_prediction_enabled;
	char    *failure_prediction_options;
	int     obsess_over_host;
	char    *notes;
	char    *notes_url;
	char    *action_url;
	char    *icon_image;
	char    *icon_image_alt;
	char    *vrml_image;
	char    *statusmap_image;
	int     have_2d_coords;
	int     x_2d;
	int     y_2d;
	int     have_3d_coords;
	double  x_3d;
	double  y_3d;
	double  z_3d;
	int     should_be_drawn;
	customvariablesmember *custom_variables;
#ifdef NSCORE
	int     problem_has_been_acknowledged;
	int     acknowledgement_type;
	int     check_type;
	int     current_state;
	int     last_state;
	int     last_hard_state;
	char	*plugin_output;
	char    *long_plugin_output;
	char    *perf_data;
        int     state_type;
	int     current_attempt;
	unsigned long current_event_id;
	unsigned long last_event_id;
	unsigned long current_problem_id;
	unsigned long last_problem_id;
	double  latency;
	double  execution_time;
	int     is_executing;
	int     check_options;
	int     notifications_enabled;
	time_t  last_host_notification;
	time_t  next_host_notification;
	time_t  next_check;
	int     should_be_scheduled;
	time_t  last_check;
	time_t	last_state_change;
	time_t	last_hard_state_change;
	time_t  last_time_up;
	time_t  last_time_down;
	time_t  last_time_unreachable;
	int     has_been_checked;
	int     is_being_freshened;
	int     notified_on_down;
	int     notified_on_unreachable;
	int     current_notification_number;
	int     no_more_notifications;
	unsigned long current_notification_id;
	int     check_flapping_recovery_notification;
	int     scheduled_downtime_depth;
	int     pending_flex_downtime;
	int     state_history[MAX_STATE_HISTORY_ENTRIES];    /* flap detection */
	int     state_history_index;
	time_t  last_state_history_update;
	int     is_flapping;
	unsigned long flapping_comment_id;
	double  percent_state_change;
	int     total_services;
	unsigned long total_service_check_interval;
	unsigned long modified_attributes;
	int     circular_path_checked;
	int     contains_circular_path;

	command *event_handler_ptr;
	command *check_command_ptr;
	timeperiod *check_period_ptr;
	timeperiod *notification_period_ptr;
	objectlist *hostgroups_ptr;
#endif
	struct  host_struct *next;
	struct  host_struct *nexthash;
        };


/* SERVICEGROUP structure */
typedef struct servicegroup_struct{
	char 	*group_name;
	char    *alias;
	servicesmember *members;
	char    *notes;
	char    *notes_url;
	char    *action_url;
	struct	servicegroup_struct *next;
	struct	servicegroup_struct *nexthash;
	}servicegroup;


/* SERVICE structure */
struct service_struct{
	char	*host_name;
	char	*description;
	char    *display_name;
        char    *service_check_command;
	char    *event_handler;
	int     initial_state;
	double	check_interval;
	double  retry_interval;
	int	max_attempts;
	int     parallelize;
	contactgroupsmember *contact_groups;
	contactsmember *contacts;
	double	notification_interval;
	double  first_notification_delay;
	int     notify_on_unknown;
	int	notify_on_warning;
	int	notify_on_critical;
	int	notify_on_recovery;
	int     notify_on_flapping;
	int     notify_on_downtime;
	int     stalk_on_ok;
	int     stalk_on_warning;
	int     stalk_on_unknown;
	int     stalk_on_critical;
	int     is_volatile;
	char	*notification_period;
	char	*check_period;
	int     flap_detection_enabled;
	double  low_flap_threshold;
	double  high_flap_threshold;
	int     flap_detection_on_ok;
	int     flap_detection_on_warning;
	int     flap_detection_on_unknown;
	int     flap_detection_on_critical;
	int     process_performance_data;
	int     check_freshness;
	int     freshness_threshold;
	int     accept_passive_service_checks;
	int     event_handler_enabled;
	int	checks_enabled;
	int     retain_status_information;
	int     retain_nonstatus_information;
	int     notifications_enabled;
	int     obsess_over_service;
	int     failure_prediction_enabled;
	char    *failure_prediction_options;
	char    *notes;
	char    *notes_url;
	char    *action_url;
	char    *icon_image;
	char    *icon_image_alt;
	customvariablesmember *custom_variables;
#ifdef NSCORE
	int     problem_has_been_acknowledged;
	int     acknowledgement_type;
	int     host_problem_at_last_check;
	int     check_type;
	int	current_state;
	int	last_state;
	int	last_hard_state;
	char	*plugin_output;
	char    *long_plugin_output;
	char    *perf_data;
        int     state_type;
	time_t	next_check;
	int     should_be_scheduled;
	time_t	last_check;
	int	current_attempt;
	unsigned long current_event_id;
	unsigned long last_event_id;
	unsigned long current_problem_id;
	unsigned long last_problem_id;
	time_t	last_notification;
	time_t  next_notification;
	int     no_more_notifications;
	int     check_flapping_recovery_notification;
	time_t	last_state_change;
	time_t	last_hard_state_change;
	time_t  last_time_ok;
	time_t  last_time_warning;
	time_t  last_time_unknown;
	time_t  last_time_critical;
	int     has_been_checked;
	int     is_being_freshened;
	int     notified_on_unknown;
	int     notified_on_warning;
	int     notified_on_critical;
	int     current_notification_number;
        unsigned long current_notification_id;
	double  latency;
	double  execution_time;
	int     is_executing;
	int     check_options;
	int     scheduled_downtime_depth;
	int     pending_flex_downtime;
	int     state_history[MAX_STATE_HISTORY_ENTRIES];    /* flap detection */
	int     state_history_index;
	int     is_flapping;
	unsigned long flapping_comment_id;
	double  percent_state_change;
	unsigned long modified_attributes;

	host *host_ptr;
	command *event_handler_ptr;
	char *event_handler_args;
	command *check_command_ptr;
	char *check_command_args;
	timeperiod *check_period_ptr;
	timeperiod *notification_period_ptr;
	objectlist *servicegroups_ptr;
#endif
	struct service_struct *next;
	struct service_struct *nexthash;
	};


/* SERVICE ESCALATION structure */
typedef struct serviceescalation_struct{
	char    *host_name;
	char    *description;
	int     first_notification;
	int     last_notification;
	double  notification_interval;
	char    *escalation_period;
	int     escalate_on_recovery;
	int     escalate_on_warning;
	int     escalate_on_unknown;
	int     escalate_on_critical;
	contactgroupsmember *contact_groups;
	contactsmember *contacts;
#ifdef NSCORE
	service *service_ptr;
	timeperiod *escalation_period_ptr;
#endif
	struct  serviceescalation_struct *next;
	struct  serviceescalation_struct *nexthash;
        }serviceescalation;


/* SERVICE DEPENDENCY structure */
typedef struct servicedependency_struct{
	int     dependency_type;
	char    *dependent_host_name;
	char    *dependent_service_description;
	char    *host_name;
	char    *service_description;
	char    *dependency_period;
	int     inherits_parent;
	int     fail_on_ok;
	int     fail_on_warning;
	int     fail_on_unknown;
	int     fail_on_critical;
	int     fail_on_pending;
#ifdef NSCORE
	int     circular_path_checked;
	int     contains_circular_path;

	service *master_service_ptr;
	service *dependent_service_ptr;
	timeperiod *dependency_period_ptr;
#endif
	struct servicedependency_struct *next;
	struct servicedependency_struct *nexthash;
        }servicedependency;


/* HOST ESCALATION structure */
typedef struct hostescalation_struct{
	char    *host_name;
	int     first_notification;
	int     last_notification;
	double  notification_interval;
	char    *escalation_period;
	int     escalate_on_recovery;
	int     escalate_on_down;
	int     escalate_on_unreachable;
	contactgroupsmember *contact_groups;
	contactsmember *contacts;
#ifdef NSCORE
	host    *host_ptr;
	timeperiod *escalation_period_ptr;
#endif
	struct  hostescalation_struct *next;
	struct  hostescalation_struct *nexthash;
        }hostescalation;


/* HOST DEPENDENCY structure */
typedef struct hostdependency_struct{
	int     dependency_type;
	char    *dependent_host_name;
	char    *host_name;
	char    *dependency_period;
	int     inherits_parent;
	int     fail_on_up;
	int     fail_on_down;
	int     fail_on_unreachable;
	int     fail_on_pending;
#ifdef NSCORE
	int     circular_path_checked;
	int     contains_circular_path;

	host    *master_host_ptr;
	host    *dependent_host_ptr;
	timeperiod *dependency_period_ptr;
#endif
	struct hostdependency_struct *next;
	struct hostdependency_struct *nexthash;
        }hostdependency;




/****************** HASH STRUCTURES ********************/

typedef struct host_cursor_struct{
	int     host_hashchain_iterator;
	host    *current_host_pointer;
        }host_cursor;





/********************* FUNCTIONS **********************/

/**** Top-level input functions ****/
int read_object_config_data(char *,int,int,int);        /* reads all external configuration data of specific types */


/**** Object Creation Functions ****/
contact *add_contact(char *,char *,char *,char *,char **,char *,char *,int,int,int,int,int,int,int,int,int,int,int,int,int,int,int,int);	/* adds a contact definition */
commandsmember *add_service_notification_command_to_contact(contact *,char *);				/* adds a service notification command to a contact definition */
commandsmember *add_host_notification_command_to_contact(contact *,char *);				/* adds a host notification command to a contact definition */
customvariablesmember *add_custom_variable_to_contact(contact *,char *,char *);                         /* adds a custom variable to a service definition */
host *add_host(char *,char *,char *,char *,char *,int,double,double,int,int,int,int,int,int,double,double,char *,int,char *,int,int,char *,int,int,double,double,int,int,int,int,int,int,int,int,char *,int,int,char *,char *,char *,char *,char *,char *,char *,int,int,int,double,double,double,int,int,int,int,int);	/* adds a host definition */
hostsmember *add_parent_host_to_host(host *,char *);							/* adds a parent host to a host definition */
hostsmember *add_child_link_to_host(host *,host *);						        /* adds a child host to a host definition */
contactgroupsmember *add_contactgroup_to_host(host *,char *);					        /* adds a contactgroup to a host definition */
contactsmember *add_contact_to_host(host *,char *);                                                     /* adds a contact to a host definition */
customvariablesmember *add_custom_variable_to_host(host *,char *,char *);                               /* adds a custom variable to a host definition */
timeperiod *add_timeperiod(char *,char *);								/* adds a timeperiod definition */
timeperiodexclusion *add_exclusion_to_timeperiod(timeperiod *,char *);                                  /* adds an exclusion to a timeperiod */
timerange *add_timerange_to_timeperiod(timeperiod *,int,unsigned long,unsigned long);			/* adds a timerange to a timeperiod definition */
daterange *add_exception_to_timeperiod(timeperiod *,int,int,int,int,int,int,int,int,int,int,int,int);
timerange *add_timerange_to_daterange(daterange *,unsigned long,unsigned long);
hostgroup *add_hostgroup(char *,char *,char *,char *,char *);						/* adds a hostgroup definition */
hostsmember *add_host_to_hostgroup(hostgroup *, char *);						/* adds a host to a hostgroup definition */
servicegroup *add_servicegroup(char *,char *,char *,char *,char *);                                     /* adds a servicegroup definition */
servicesmember *add_service_to_servicegroup(servicegroup *,char *,char *);                              /* adds a service to a servicegroup definition */
contactgroup *add_contactgroup(char *,char *);								/* adds a contactgroup definition */
contactsmember *add_contact_to_contactgroup(contactgroup *,char *);					/* adds a contact to a contact group definition */
command *add_command(char *,char *);									/* adds a command definition */
service *add_service(char *,char *,char *,char *,int,int,int,int,double,double,double,double,char *,int,int,int,int,int,int,int,int,char *,int,char *,int,int,double,double,int,int,int,int,int,int,int,int,int,int,char *,int,int,char *,char *,char *,char *,char *,int,int,int);	/* adds a service definition */
contactgroupsmember *add_contactgroup_to_service(service *,char *);					/* adds a contact group to a service definition */
contactsmember *add_contact_to_service(service *,char *);                                               /* adds a contact to a host definition */
serviceescalation *add_serviceescalation(char *,char *,int,int,double,char *,int,int,int,int);          /* adds a service escalation definition */
contactgroupsmember *add_contactgroup_to_serviceescalation(serviceescalation *,char *);                 /* adds a contact group to a service escalation definition */
contactsmember *add_contact_to_serviceescalation(serviceescalation *,char *);                           /* adds a contact to a service escalation definition */
customvariablesmember *add_custom_variable_to_service(service *,char *,char *);                         /* adds a custom variable to a service definition */
servicedependency *add_service_dependency(char *,char *,char *,char *,int,int,int,int,int,int,int,char *);     /* adds a service dependency definition */
hostdependency *add_host_dependency(char *,char *,int,int,int,int,int,int,char *);                             /* adds a host dependency definition */
hostescalation *add_hostescalation(char *,int,int,double,char *,int,int,int);                           /* adds a host escalation definition */
contactsmember *add_contact_to_hostescalation(hostescalation *,char *);                                 /* adds a contact to a host escalation definition */
contactgroupsmember *add_contactgroup_to_hostescalation(hostescalation *,char *);                       /* adds a contact group to a host escalation definition */

contactsmember *add_contact_to_object(contactsmember **,char *);                                        /* adds a contact to an object */ 
customvariablesmember *add_custom_variable_to_object(customvariablesmember **,char *,char *);           /* adds a custom variable to an object */


servicesmember *add_service_link_to_host(host *,service *);


/*** Object Skiplist Functions ****/
int init_object_skiplists(void);
int free_object_skiplists(void);
int skiplist_compare_text(const char *val1a, const char *val1b, const char *val2a, const char *val2b);
int skiplist_compare_host(void *a, void *b);
int skiplist_compare_service(void *a, void *b);
int skiplist_compare_command(void *a, void *b);
int skiplist_compare_timeperiod(void *a, void *b);
int skiplist_compare_contact(void *a, void *b);
int skiplist_compare_contactgroup(void *a, void *b);
int skiplist_compare_hostgroup(void *a, void *b);
int skiplist_compare_servicegroup(void *a, void *b);
int skiplist_compare_hostescalation(void *a, void *b);
int skiplist_compare_serviceescalation(void *a, void *b);
int skiplist_compare_hostdependency(void *a, void *b);
int skiplist_compare_servicedependency(void *a, void *b);

int get_host_count(void);
int get_service_count(void);



/**** Object Hash Functions ****/
int add_servicedependency_to_hashlist(servicedependency *);


/**** Object Search Functions ****/
timeperiod * find_timeperiod(char *);						                /* finds a timeperiod object */
host * find_host(char *);									/* finds a host object */
hostgroup * find_hostgroup(char *);						                /* finds a hostgroup object */
servicegroup * find_servicegroup(char *);					                /* finds a servicegroup object */
contact * find_contact(char *);							                /* finds a contact object */
contactgroup * find_contactgroup(char *);					                /* finds a contactgroup object */
command * find_command(char *);							                /* finds a command object */
service * find_service(char *,char *);								/* finds a service object */


/**** Object Traversal Functions ****/
hostescalation *get_first_hostescalation_by_host(char *, void **);
hostescalation *get_next_hostescalation_by_host(char *,void **);
serviceescalation *get_first_serviceescalation_by_service(char *,char *, void **);
serviceescalation *get_next_serviceescalation_by_service(char *,char *,void **);
hostdependency *get_first_hostdependency_by_dependent_host(char *, void **);
hostdependency *get_next_hostdependency_by_dependent_host(char *, void **);
servicedependency *get_first_servicedependency_by_dependent_service(char *,char *, void **);
servicedependency *get_next_servicedependency_by_dependent_service(char *,char *,void **);

#ifdef NSCORE
int add_object_to_objectlist(objectlist **,void *);
int free_objectlist(objectlist **);
#endif


/**** Object Query Functions ****/
int is_host_immediate_child_of_host(host *,host *);	                /* checks if a host is an immediate child of another host */	
int is_host_primary_immediate_child_of_host(host *,host *);             /* checks if a host is an immediate child (and primary child) of another host */
int is_host_immediate_parent_of_host(host *,host *);	                /* checks if a host is an immediate child of another host */	
int is_host_member_of_hostgroup(hostgroup *,host *);		        /* tests whether or not a host is a member of a specific hostgroup */
int is_host_member_of_servicegroup(servicegroup *,host *);	        /* tests whether or not a service is a member of a specific servicegroup */
int is_service_member_of_servicegroup(servicegroup *,service *);	/* tests whether or not a service is a member of a specific servicegroup */
int is_contact_member_of_contactgroup(contactgroup *, contact *);	/* tests whether or not a contact is a member of a specific contact group */
int is_contact_for_hostgroup(hostgroup *,contact *);	                /* tests whether or not a contact is a member of a specific hostgroup */
int is_contact_for_servicegroup(servicegroup *,contact *);	        /* tests whether or not a contact is a member of a specific servicegroup */
int is_contact_for_host(host *,contact *);			        /* tests whether or not a contact is a contact member for a specific host */
int is_escalated_contact_for_host(host *,contact *);                    /* checks whether or not a contact is an escalated contact for a specific host */
int is_contact_for_service(service *,contact *);		        /* tests whether or not a contact is a contact member for a specific service */
int is_escalated_contact_for_service(service *,contact *);              /* checks whether or not a contact is an escalated contact for a specific service */
int is_host_immediate_parent_of_host(host *,host *);		        /* tests whether or not a host is an immediate parent of another host */

int number_of_immediate_child_hosts(host *);		                /* counts the number of immediate child hosts for a particular host */
int number_of_total_child_hosts(host *);				/* counts the number of total child hosts for a particular host */
int number_of_immediate_parent_hosts(host *);				/* counts the number of immediate parents hosts for a particular host */
int number_of_total_parent_hosts(host *);				/* counts the number of total parents hosts for a particular host */

#ifdef NSCORE
int check_for_circular_servicedependency_path(servicedependency *,servicedependency *,int);   /* checks if a circular dependency exists for a given service */
int check_for_circular_hostdependency_path(hostdependency *,hostdependency *,int);   /* checks if a circular dependency exists for a given host */
#endif


/**** Object Cleanup Functions ****/
int free_object_data(void);                             /* frees all allocated memory for the object definitions */




#ifdef __cplusplus
  }
#endif

#endif
