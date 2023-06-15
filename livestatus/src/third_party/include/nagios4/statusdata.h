/*****************************************************************************
 *
 * STATUSDATA.H - Header for external status data routines
 *
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

#ifndef _STATUSDATA_H
#define _STATUSDATA_H

#include "common.h"
#include "objects.h"

#ifdef NSCGI
#define READ_PROGRAM_STATUS	1
#define READ_HOST_STATUS	2
#define READ_SERVICE_STATUS	4
#define READ_CONTACT_STATUS     8

#define READ_ALL_STATUS_DATA    READ_PROGRAM_STATUS | READ_HOST_STATUS | READ_SERVICE_STATUS | READ_CONTACT_STATUS



	/*************************** CHAINED HASH LIMITS ***************************/

#define SERVICESTATUS_HASHSLOTS      1024
#define HOSTSTATUS_HASHSLOTS         1024


	/**************************** DATA STRUCTURES ******************************/

NAGIOS_BEGIN_DECL

/* HOST STATUS structure */
typedef struct hoststatus_struct {
	char    *host_name;
	char    *plugin_output;
	char    *long_plugin_output;
	char    *perf_data;
	int     status;
	time_t  last_update;
	int     has_been_checked;
	int     should_be_scheduled;
	int     current_attempt;
	int     max_attempts;
	time_t  last_check;
	time_t  next_check;
	int     check_options;
	int     check_type;
	time_t	last_state_change;
	time_t	last_hard_state_change;
	int     last_hard_state;
	time_t  last_time_up;
	time_t  last_time_down;
	time_t  last_time_unreachable;
	int     state_type;
	time_t  last_notification;
	time_t  next_notification;
	int     no_more_notifications;
	int     notifications_enabled;
	int     problem_has_been_acknowledged;
	int     acknowledgement_type;
	int     current_notification_number;
	int     accept_passive_checks;
	int     event_handler_enabled;
	int     checks_enabled;
	int     flap_detection_enabled;
	int     is_flapping;
	double  percent_state_change;
	double  latency;
	double  execution_time;
	int     scheduled_downtime_depth;
	int     process_performance_data;
	int     obsess;
	struct  hoststatus_struct *next;
	struct  hoststatus_struct *nexthash;
	} hoststatus;


/* SERVICE STATUS structure */
typedef struct servicestatus_struct {
	char    *host_name;
	char    *description;
	char    *plugin_output;
	char    *long_plugin_output;
	char    *perf_data;
	int     max_attempts;
	int     current_attempt;
	int     status;
	time_t  last_update;
	int     has_been_checked;
	int     should_be_scheduled;
	time_t  last_check;
	time_t  next_check;
	int     check_options;
	int     check_type;
	int	checks_enabled;
	time_t	last_state_change;
	time_t	last_hard_state_change;
	int	last_hard_state;
	time_t  last_time_ok;
	time_t  last_time_warning;
	time_t  last_time_unknown;
	time_t  last_time_critical;
	int     state_type;
	time_t  last_notification;
	time_t  next_notification;
	int     no_more_notifications;
	int     notifications_enabled;
	int     problem_has_been_acknowledged;
	int     acknowledgement_type;
	int     current_notification_number;
	int     accept_passive_checks;
	int     event_handler_enabled;
	int     flap_detection_enabled;
	int     is_flapping;
	double  percent_state_change;
	double  latency;
	double  execution_time;
	int     scheduled_downtime_depth;
	int     process_performance_data;
	int     obsess;
	struct  servicestatus_struct *next;
	struct  servicestatus_struct *nexthash;
	} servicestatus;


/*************************** SERVICE STATES ***************************/

#define SERVICE_PENDING			1
#define SERVICE_OK			2
#define SERVICE_WARNING			4
#define SERVICE_UNKNOWN			8
#define SERVICE_CRITICAL		16



/**************************** HOST STATES ****************************/

#define HOST_PENDING			1
#define SD_HOST_UP				2
#define SD_HOST_DOWN			4
#define SD_HOST_UNREACHABLE		8

/* Convert the (historically ordered) host states into a notion of "urgency".
	  This is defined as, in ascending order:
		SD_HOST_UP			(business as usual)
		HOST_PENDING		(waiting for - supposedly first - check result)
		SD_HOST_UNREACHABLE	(a problem, but likely not its cause)
		SD_HOST_DOWN		(look here!!)
	  The exact values are irrelevant, so I try to make the conversion as
	  CPU-efficient as possible: */
#define HOST_URGENCY(hs)		((hs)|(((hs)&0x5)<<1))



/**************************** FUNCTIONS ******************************/

int read_status_data(const char *, int);                /* reads all status data */
int add_host_status(hoststatus *);                      /* adds a host status entry to the list in memory */
int add_service_status(servicestatus *);                /* adds a service status entry to the list in memory */

int add_hoststatus_to_hashlist(hoststatus *);
int add_servicestatus_to_hashlist(servicestatus *);

servicestatus *find_servicestatus(char *, char *);      /* finds status information for a specific service */
hoststatus *find_hoststatus(char *);                    /* finds status information for a specific host */
int get_servicestatus_count(char *, int);		/* gets total number of services of a certain type for a specific host */

void free_status_data(void);                            /* free all memory allocated to status data */
#endif

#ifndef NSCGI
int initialize_status_data(const char *);               /* initializes status data at program start */
int update_all_status_data(void);                       /* updates all status data */
int cleanup_status_data(int);                           /* cleans up status data at program termination */
int update_program_status(int);                         /* updates program status data */
int update_host_status(host *, int);                    /* updates host status data */
int update_service_status(service *, int);              /* updates service status data */
int update_contact_status(contact *, int);              /* updates contact status data */
#endif

NAGIOS_END_DECL
#endif
