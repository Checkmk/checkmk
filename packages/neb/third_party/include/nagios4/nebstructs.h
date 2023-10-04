/*****************************************************************************
 *
 * NEBSTRUCTS.H - Event broker includes for Nagios
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

#ifndef _NEBSTRUCTS_H
#define _NEBSTRUCTS_H

#include "common.h"
#include "objects.h"
#include "nagios.h"

NAGIOS_BEGIN_DECL

/****** STRUCTURES *************************/

/* process data structure */
typedef struct nebstruct_process_struct {
	int             type;
	int             flags;
	int             attr;
	struct timeval  timestamp;
	} nebstruct_process_data;


/* timed event data structure */
typedef struct nebstruct_timed_event_struct {
	int             type;
	int             flags;
	int             attr;
	struct timeval  timestamp;

	int             event_type;
	int             recurring;
	time_t          run_time;
	void            *event_data;

	void            *event_ptr;
	} nebstruct_timed_event_data;


/* log data structure */
typedef struct nebstruct_log_struct {
	int             type;
	int             flags;
	int             attr;
	struct timeval  timestamp;

	time_t          entry_time;
	int             data_type;
	char            *data;
	} nebstruct_log_data;


/* system command structure */
typedef struct nebstruct_system_command_struct {
	int             type;
	int             flags;
	int             attr;
	struct timeval  timestamp;

	struct timeval  start_time;
	struct timeval  end_time;
	int             timeout;
	char            *command_line;
	int             early_timeout;
	double          execution_time;
	int             return_code;
	char            *output;
	} nebstruct_system_command_data;


/* event handler structure */
typedef struct nebstruct_event_handler_struct {
	int             type;
	int             flags;
	int             attr;
	struct timeval  timestamp;

	int             eventhandler_type;
	char            *host_name;
	char            *service_description;
	int             state_type;
	int             state;
	int             timeout;
	char            *command_name;
	char            *command_args;
	char            *command_line;
	struct timeval  start_time;
	struct timeval  end_time;
	int             early_timeout;
	double          execution_time;
	int             return_code;
	char            *output;

	void            *object_ptr;
	} nebstruct_event_handler_data;


/* host check structure */
typedef struct nebstruct_host_check_struct {
	int             type;
	int             flags;
	int             attr;
	struct timeval  timestamp;

	char            *host_name;
	int             current_attempt;
	int             check_type;
	int             max_attempts;
	int             state_type;
	int             state;
	int             timeout;
	char            *command_name;
	char            *command_args;
	char            *command_line;
	struct timeval  start_time;
	struct timeval  end_time;
	int             early_timeout;
	double          execution_time;
	double          latency;
	int             return_code;
	char            *output;
	char            *long_output;
	char            *perf_data;
	check_result    *check_result_ptr;

	void            *object_ptr;
	} nebstruct_host_check_data;


/* service check structure */
typedef struct nebstruct_service_check_struct {
	int             type;
	int             flags;
	int             attr;
	struct timeval  timestamp;

	char            *host_name;
	char            *service_description;
	int             check_type;
	int             current_attempt;
	int             max_attempts;
	int             state_type;
	int             state;
	int             timeout;
	char            *command_name;
	char            *command_args;
	char            *command_line;
	struct timeval  start_time;
	struct timeval  end_time;
	int             early_timeout;
	double          execution_time;
	double          latency;
	int             return_code;
	char            *output;
	char            *long_output;
	char            *perf_data;
	check_result    *check_result_ptr;

	void            *object_ptr;
	} nebstruct_service_check_data;


/* comment data structure */
typedef struct nebstruct_comment_struct {
	int             type;
	int             flags;
	int             attr;
	struct timeval  timestamp;

	int             comment_type;
	char            *host_name;
	char            *service_description;
	time_t          entry_time;
	char            *author_name;
	char            *comment_data;
	int             persistent;
	int             source;
	int             entry_type;
	int             expires;
	time_t          expire_time;
	unsigned long   comment_id;

	void            *object_ptr; /* not implemented yet */
	} nebstruct_comment_data;


/* downtime data structure */
typedef struct nebstruct_downtime_struct {
	int             type;
	int             flags;
	int             attr;
	struct timeval  timestamp;

	int             downtime_type;
	char            *host_name;
	char            *service_description;
	time_t          entry_time;
	char            *author_name;
	char            *comment_data;
	time_t          start_time;
	time_t          end_time;
	int             fixed;
	unsigned long   duration;
	unsigned long   triggered_by;
	unsigned long   downtime_id;

	void            *object_ptr; /* not implemented yet */
	} nebstruct_downtime_data;


/* flapping data structure */
typedef struct nebstruct_flapping_struct {
	int             type;
	int             flags;
	int             attr;
	struct timeval  timestamp;

	int             flapping_type;
	char            *host_name;
	char            *service_description;
	double          percent_change;
	double          high_threshold;
	double          low_threshold;
	unsigned long   comment_id;

	void            *object_ptr;
	} nebstruct_flapping_data;


/* program status structure */
typedef struct nebstruct_program_status_struct {
	int             type;
	int             flags;
	int             attr;
	struct timeval  timestamp;

	time_t          program_start;
	int             pid;
	int             daemon_mode;
	time_t          last_log_rotation;
	int             notifications_enabled;
	int             active_service_checks_enabled;
	int             passive_service_checks_enabled;
	int             active_host_checks_enabled;
	int             passive_host_checks_enabled;
	int             event_handlers_enabled;
	int             flap_detection_enabled;
	int             process_performance_data;
	int             obsess_over_hosts;
	int             obsess_over_services;
	unsigned long   modified_host_attributes;
	unsigned long   modified_service_attributes;
	char            *global_host_event_handler;
	char            *global_service_event_handler;
	} nebstruct_program_status_data;


/* host status structure */
typedef struct nebstruct_host_status_struct {
	int             type;
	int             flags;
	int             attr;
	struct timeval  timestamp;

	void            *object_ptr;
	} nebstruct_host_status_data;


/* service status structure */
typedef struct nebstruct_service_status_struct {
	int             type;
	int             flags;
	int             attr;
	struct timeval  timestamp;

	void            *object_ptr;
	} nebstruct_service_status_data;


/* contact status structure */
typedef struct nebstruct_contact_status_struct {
	int             type;
	int             flags;
	int             attr;
	struct timeval  timestamp;

	void            *object_ptr;
	} nebstruct_contact_status_data;


/* notification data structure */
typedef struct nebstruct_notification_struct {
	int             type;
	int             flags;
	int             attr;
	struct timeval  timestamp;

	int             notification_type;
	struct timeval  start_time;
	struct timeval  end_time;
	char            *host_name;
	char            *service_description;
	int             reason_type;
	int             state;
	char            *output;
	char            *ack_author;
	char            *ack_data;
	int             escalated;
	int             contacts_notified;

	void            *object_ptr;
	} nebstruct_notification_data;


/* contact notification data structure */
typedef struct nebstruct_contact_notification_struct {
	int             type;
	int             flags;
	int             attr;
	struct timeval  timestamp;

	int             notification_type;
	struct timeval  start_time;
	struct timeval  end_time;
	char            *host_name;
	char            *service_description;
	char            *contact_name;
	int             reason_type;
	int             state;
	char            *output;
	char            *ack_author;
	char            *ack_data;
	int             escalated;

	void            *object_ptr;
	void            *contact_ptr;
	} nebstruct_contact_notification_data;


/* contact notification method data structure */
typedef struct nebstruct_contact_notification_method_struct {
	int             type;
	int             flags;
	int             attr;
	struct timeval  timestamp;

	int             notification_type;
	struct timeval  start_time;
	struct timeval  end_time;
	char            *host_name;
	char            *service_description;
	char            *contact_name;
	char            *command_name;
	char            *command_args;
	int             reason_type;
	int             state;
	char            *output;
	char            *ack_author;
	char            *ack_data;
	int             escalated;

	void            *object_ptr;
	void            *contact_ptr;
	} nebstruct_contact_notification_method_data;


/* adaptive program data structure */
typedef struct nebstruct_adaptive_program_data_struct {
	int             type;
	int             flags;
	int             attr;
	struct timeval  timestamp;

	int             command_type;
	unsigned long   modified_host_attribute;
	unsigned long   modified_host_attributes;
	unsigned long   modified_service_attribute;
	unsigned long   modified_service_attributes;
	} nebstruct_adaptive_program_data;


/* adaptive host data structure */
typedef struct nebstruct_adaptive_host_data_struct {
	int             type;
	int             flags;
	int             attr;
	struct timeval  timestamp;

	int             command_type;
	unsigned long   modified_attribute;
	unsigned long   modified_attributes;

	void            *object_ptr;
	} nebstruct_adaptive_host_data;


/* adaptive service data structure */
typedef struct nebstruct_adaptive_service_data_struct {
	int             type;
	int             flags;
	int             attr;
	struct timeval  timestamp;

	int             command_type;
	unsigned long   modified_attribute;
	unsigned long   modified_attributes;

	void            *object_ptr;
	} nebstruct_adaptive_service_data;


/* adaptive contact data structure */
typedef struct nebstruct_adaptive_contact_data_struct {
	int             type;
	int             flags;
	int             attr;
	struct timeval  timestamp;

	int             command_type;
	unsigned long   modified_attribute;
	unsigned long   modified_attributes;
	unsigned long   modified_host_attribute;
	unsigned long   modified_host_attributes;
	unsigned long   modified_service_attribute;
	unsigned long   modified_service_attributes;

	void            *object_ptr;
	} nebstruct_adaptive_contact_data;


/* external command data structure */
typedef struct nebstruct_external_command_struct {
	int             type;
	int             flags;
	int             attr;
	struct timeval  timestamp;

	int             command_type;
	time_t          entry_time;
	char            *command_string;
	char            *command_args;
	} nebstruct_external_command_data;


/* aggregated status data structure */
typedef struct nebstruct_aggregated_status_struct {
	int             type;
	int             flags;
	int             attr;
	struct timeval  timestamp;

	} nebstruct_aggregated_status_data;


/* retention data structure */
typedef struct nebstruct_retention_struct {
	int             type;
	int             flags;
	int             attr;
	struct timeval  timestamp;

	} nebstruct_retention_data;


/* acknowledgement structure */
typedef struct nebstruct_acknowledgement_struct {
	int             type;
	int             flags;
	int             attr;
	struct timeval  timestamp;

	int             acknowledgement_type;
	char            *host_name;
	char            *service_description;
	int             state;
	char            *author_name;
	char            *comment_data;
	int             is_sticky;
	int             persistent_comment;
	int             notify_contacts;

	void            *object_ptr;
	} nebstruct_acknowledgement_data;


/* state change structure */
typedef struct nebstruct_statechange_struct {
	int             type;
	int             flags;
	int             attr;
	struct timeval  timestamp;

	int             statechange_type;
	char            *host_name;
	char            *service_description;
	int             state;
	int             state_type;
	int             current_attempt;
	int             max_attempts;
	char            *output;

	void            *object_ptr;
	} nebstruct_statechange_data;

NAGIOS_END_DECL
#endif
