/*****************************************************************************
 *
 * DOWNTIME.H - Header file for scheduled downtime functions
 *
 * Copyright (c) 2001-2005 Ethan Galstad (egalstad@nagios.org)
 * Last Modified:   11-25-2005
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


#ifndef _DOWNTIME_H
#define _DOWNTIME_H

#include "config.h"
#include "common.h"
#include "objects.h"

#ifdef __cplusplus
  extern "C" {
#endif

/* SCHEDULED_DOWNTIME_ENTRY structure */
typedef struct scheduled_downtime_struct{
	int type;
	char *host_name;
	char *service_description;
	time_t entry_time;
	time_t start_time;
	time_t end_time;
	int fixed;
	unsigned long triggered_by;
	unsigned long duration;
	unsigned long downtime_id;
	char *author;
	char *comment;
#ifdef NSCORE
	unsigned long comment_id;
	int is_in_effect;
	int start_flex_downtime;
	int incremented_pending_downtime;
#endif
	struct scheduled_downtime_struct *next;
	}scheduled_downtime;



#ifdef NSCORE
int initialize_downtime_data(char *);                                /* initializes scheduled downtime data */
int cleanup_downtime_data(char *);                                   /* cleans up scheduled downtime data */

int add_new_downtime(int,char *,char *,time_t,char *,char *,time_t,time_t,int,unsigned long,unsigned long,unsigned long *);
int add_new_host_downtime(char *,time_t,char *,char *,time_t,time_t,int,unsigned long,unsigned long,unsigned long *);
int add_new_service_downtime(char *,char *,time_t,char *,char *,time_t,time_t,int,unsigned long,unsigned long,unsigned long *);

int delete_host_downtime(unsigned long);
int delete_service_downtime(unsigned long);
int delete_downtime(int,unsigned long);

int schedule_downtime(int,char *,char *,time_t,char *,char *,time_t,time_t,int,unsigned long,unsigned long,unsigned long *);
int unschedule_downtime(int,unsigned long);

int register_downtime(int,unsigned long);
int handle_scheduled_downtime(scheduled_downtime *);
int handle_scheduled_downtime_by_id(unsigned long);

int check_pending_flex_host_downtime(host *);
int check_pending_flex_service_downtime(service *);

int check_for_expired_downtime(void);
#endif

int add_host_downtime(char *,time_t,char *,char *,time_t,time_t,int,unsigned long,unsigned long,unsigned long);
int add_service_downtime(char *,char *,time_t,char *,char *,time_t,time_t,int,unsigned long,unsigned long,unsigned long);
int add_downtime(int,char *,char *,time_t,char *,char *,time_t,time_t,int,unsigned long,unsigned long,unsigned long);

scheduled_downtime *find_downtime(int,unsigned long);
scheduled_downtime *find_host_downtime(unsigned long);
scheduled_downtime *find_service_downtime(unsigned long);

void free_downtime_data(void);                                       /* frees memory allocated to scheduled downtime list */

#ifdef __cplusplus
  }
#endif

#endif
