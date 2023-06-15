/*****************************************************************************
 *
 * COMMENTS.H - Header file for comment functions
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


#ifndef _COMMENTS_H
#define _COMMENTS_H
#include "common.h"
#include "objects.h"


/**************************** COMMENT SOURCES ******************************/

#define COMMENTSOURCE_INTERNAL  0
#define COMMENTSOURCE_EXTERNAL  1



/***************************** COMMENT TYPES *******************************/

#define HOST_COMMENT			1
#define SERVICE_COMMENT			2


/****************************** ENTRY TYPES ********************************/

#define USER_COMMENT                    1
#define DOWNTIME_COMMENT                2
#define FLAPPING_COMMENT                3
#define ACKNOWLEDGEMENT_COMMENT         4


/*************************** CHAINED HASH LIMITS ***************************/

#define COMMENT_HASHSLOTS      1024


/**************************** DATA STRUCTURES ******************************/

NAGIOS_BEGIN_DECL

/* COMMENT structure */
typedef struct comment {
	int 	comment_type;
	int     entry_type;
	unsigned long comment_id;
	int     source;
	int     persistent;
	time_t 	entry_time;
	int     expires;
	time_t  expire_time;
	char 	*host_name;
	char 	*service_description;
	char 	*author;
	char 	*comment_data;
	struct 	comment *next;
	struct 	comment *nexthash;
	} comment;

extern struct comment *comment_list;

#ifndef NSCGI
int initialize_comment_data(void);                                /* initializes comment data */
int add_new_comment(int, int, char *, char *, time_t, char *, char *, int, int, int, time_t, unsigned long *); /* adds a new host or service comment */
int add_new_host_comment(int, char *, time_t, char *, char *, int, int, int, time_t, unsigned long *);    /* adds a new host comment */
int add_new_service_comment(int, char *, char *, time_t, char *, char *, int, int, int, time_t, unsigned long *); /* adds a new service comment */
int delete_comment(int, unsigned long);                             /* deletes a host or service comment */
int delete_host_comment(unsigned long);                             /* deletes a host comment */
int delete_service_comment(unsigned long);                          /* deletes a service comment */
int delete_all_comments(int, char *, char *);                       /* deletes all comments for a particular host or service */
int delete_all_host_comments(char *);                               /* deletes all comments for a specific host */
int delete_host_acknowledgement_comments(struct host *);                   /* deletes all non-persistent ack comments for a specific host */
int delete_all_service_comments(char *, char *);                    /* deletes all comments for a specific service */
int delete_service_acknowledgement_comments(struct service *);             /* deletes all non-persistent ack comments for a specific service */

int check_for_expired_comment(unsigned long);                       /* expires a comment */
#endif

struct comment *find_comment(unsigned long, int);                            /* finds a specific comment */
struct comment *find_service_comment(unsigned long);                         /* finds a specific service comment */
struct comment *find_host_comment(unsigned long);                            /* finds a specific host comment */

struct comment *get_first_comment_by_host(char *);
struct comment *get_next_comment_by_host(char *, struct comment *);

int number_of_host_comments(char *);			              /* returns the number of comments associated with a particular host */
int number_of_service_comments(char *, char *);		              /* returns the number of comments associated with a particular service */

int add_comment(int, int, char *, char *, time_t, char *, char *, unsigned long, int, int, time_t, int); /* adds a comment (host or service) */
int sort_comments(void);
int add_host_comment(int, char *, time_t, char *, char *, unsigned long, int, int, time_t, int);   /* adds a host comment */
int add_service_comment(int, char *, char *, time_t, char *, char *, unsigned long, int, int, time_t, int); /* adds a service comment */

int add_comment_to_hashlist(struct comment *);

void free_comment_data(void);                                             /* frees memory allocated to the comment list */

NAGIOS_BEGIN_DECL

#endif
