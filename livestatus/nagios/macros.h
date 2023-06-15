/************************************************************************
 *
 * MACROS.H - Common macro functions
 * Written By: Ethan Galstad (egalstad@nagios.org)
 * Last Modified: 10-28-2007
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

#ifndef _MACROS_H
#define _MACROS_H

#include "config.h"
#include "common.h"
#include "objects.h"



/****************** LENGTH LIMITATIONS ****************/

#define MAX_COMMAND_ARGUMENTS			32	/* maximum number of $ARGx$ macros */


/****************** MACRO DEFINITIONS *****************/

#define MACRO_ENV_VAR_PREFIX			"NAGIOS_"

#define MAX_USER_MACROS				256	/* maximum number of $USERx$ macros */

#define MACRO_X_COUNT				153	/* size of macro_x[] array */

#define MACRO_HOSTNAME				0
#define MACRO_HOSTALIAS				1
#define MACRO_HOSTADDRESS			2
#define MACRO_SERVICEDESC			3
#define MACRO_SERVICESTATE			4
#define MACRO_SERVICESTATEID                    5
#define MACRO_SERVICEATTEMPT			6
#define MACRO_LONGDATETIME			7
#define MACRO_SHORTDATETIME			8
#define MACRO_DATE				9
#define MACRO_TIME				10
#define MACRO_TIMET				11
#define MACRO_LASTHOSTCHECK			12
#define MACRO_LASTSERVICECHECK			13
#define MACRO_LASTHOSTSTATECHANGE		14
#define MACRO_LASTSERVICESTATECHANGE		15
#define MACRO_HOSTOUTPUT			16
#define MACRO_SERVICEOUTPUT			17
#define MACRO_HOSTPERFDATA			18
#define MACRO_SERVICEPERFDATA			19
#define MACRO_CONTACTNAME			20
#define MACRO_CONTACTALIAS			21
#define MACRO_CONTACTEMAIL			22
#define MACRO_CONTACTPAGER			23
#define MACRO_ADMINEMAIL			24
#define MACRO_ADMINPAGER			25
#define MACRO_HOSTSTATE				26
#define MACRO_HOSTSTATEID                       27
#define MACRO_HOSTATTEMPT			28
#define MACRO_NOTIFICATIONTYPE			29
#define MACRO_NOTIFICATIONNUMBER		30   /* deprecated - see HOSTNOTIFICATIONNUMBER and SERVICENOTIFICATIONNUMBER macros */
#define MACRO_HOSTEXECUTIONTIME			31
#define MACRO_SERVICEEXECUTIONTIME		32
#define MACRO_HOSTLATENCY                       33
#define MACRO_SERVICELATENCY			34
#define MACRO_HOSTDURATION			35
#define MACRO_SERVICEDURATION			36
#define MACRO_HOSTDURATIONSEC			37
#define MACRO_SERVICEDURATIONSEC		38
#define MACRO_HOSTDOWNTIME			39
#define MACRO_SERVICEDOWNTIME			40
#define MACRO_HOSTSTATETYPE			41
#define MACRO_SERVICESTATETYPE			42
#define MACRO_HOSTPERCENTCHANGE			43
#define MACRO_SERVICEPERCENTCHANGE		44
#define MACRO_HOSTGROUPNAME			45
#define MACRO_HOSTGROUPALIAS			46
#define MACRO_SERVICEGROUPNAME			47
#define MACRO_SERVICEGROUPALIAS			48
#define MACRO_HOSTACKAUTHOR                     49
#define MACRO_HOSTACKCOMMENT                    50
#define MACRO_SERVICEACKAUTHOR                  51
#define MACRO_SERVICEACKCOMMENT                 52
#define MACRO_LASTSERVICEOK                     53
#define MACRO_LASTSERVICEWARNING                54
#define MACRO_LASTSERVICEUNKNOWN                55
#define MACRO_LASTSERVICECRITICAL               56
#define MACRO_LASTHOSTUP                        57
#define MACRO_LASTHOSTDOWN                      58
#define MACRO_LASTHOSTUNREACHABLE               59
#define MACRO_SERVICECHECKCOMMAND		60
#define MACRO_HOSTCHECKCOMMAND			61
#define MACRO_MAINCONFIGFILE			62
#define MACRO_STATUSDATAFILE			63
#define MACRO_HOSTDISPLAYNAME			64
#define MACRO_SERVICEDISPLAYNAME		65
#define MACRO_RETENTIONDATAFILE			66
#define MACRO_OBJECTCACHEFILE			67
#define MACRO_TEMPFILE				68
#define MACRO_LOGFILE				69
#define MACRO_RESOURCEFILE			70
#define MACRO_COMMANDFILE			71
#define MACRO_HOSTPERFDATAFILE			72
#define MACRO_SERVICEPERFDATAFILE		73
#define MACRO_HOSTACTIONURL			74
#define MACRO_HOSTNOTESURL			75
#define MACRO_HOSTNOTES				76
#define MACRO_SERVICEACTIONURL			77
#define MACRO_SERVICENOTESURL			78
#define MACRO_SERVICENOTES			79
#define MACRO_TOTALHOSTSUP			80
#define MACRO_TOTALHOSTSDOWN			81
#define MACRO_TOTALHOSTSUNREACHABLE		82
#define MACRO_TOTALHOSTSDOWNUNHANDLED		83
#define MACRO_TOTALHOSTSUNREACHABLEUNHANDLED	84
#define MACRO_TOTALHOSTPROBLEMS			85
#define MACRO_TOTALHOSTPROBLEMSUNHANDLED	86
#define MACRO_TOTALSERVICESOK			87
#define MACRO_TOTALSERVICESWARNING		88
#define MACRO_TOTALSERVICESCRITICAL		89
#define MACRO_TOTALSERVICESUNKNOWN		90
#define MACRO_TOTALSERVICESWARNINGUNHANDLED	91
#define MACRO_TOTALSERVICESCRITICALUNHANDLED	92
#define MACRO_TOTALSERVICESUNKNOWNUNHANDLED	93
#define MACRO_TOTALSERVICEPROBLEMS		94
#define MACRO_TOTALSERVICEPROBLEMSUNHANDLED	95
#define MACRO_PROCESSSTARTTIME			96
#define MACRO_HOSTCHECKTYPE			97
#define MACRO_SERVICECHECKTYPE			98
#define MACRO_LONGHOSTOUTPUT	                99
#define MACRO_LONGSERVICEOUTPUT                 100
#define MACRO_TEMPPATH                          101
#define MACRO_HOSTNOTIFICATIONNUMBER            102
#define MACRO_SERVICENOTIFICATIONNUMBER         103
#define MACRO_HOSTNOTIFICATIONID                104
#define MACRO_SERVICENOTIFICATIONID             105
#define MACRO_HOSTEVENTID                       106
#define MACRO_LASTHOSTEVENTID                   107
#define MACRO_SERVICEEVENTID                    108
#define MACRO_LASTSERVICEEVENTID                109
#define MACRO_HOSTGROUPNAMES                    110
#define MACRO_SERVICEGROUPNAMES                 111
#define MACRO_HOSTACKAUTHORNAME                 112
#define MACRO_HOSTACKAUTHORALIAS                113
#define MACRO_SERVICEACKAUTHORNAME              114
#define MACRO_SERVICEACKAUTHORALIAS             115
#define MACRO_MAXHOSTATTEMPTS			116
#define MACRO_MAXSERVICEATTEMPTS		117
#define MACRO_SERVICEISVOLATILE			118
#define MACRO_TOTALHOSTSERVICES			119
#define MACRO_TOTALHOSTSERVICESOK		120
#define MACRO_TOTALHOSTSERVICESWARNING		121
#define MACRO_TOTALHOSTSERVICESUNKNOWN		122
#define MACRO_TOTALHOSTSERVICESCRITICAL		123
#define MACRO_HOSTGROUPNOTES                    124
#define MACRO_HOSTGROUPNOTESURL                 125
#define MACRO_HOSTGROUPACTIONURL                126
#define MACRO_SERVICEGROUPNOTES                 127
#define MACRO_SERVICEGROUPNOTESURL              128
#define MACRO_SERVICEGROUPACTIONURL             129
#define MACRO_HOSTGROUPMEMBERS                  130
#define MACRO_SERVICEGROUPMEMBERS               131
#define MACRO_CONTACTGROUPNAME                  132
#define MACRO_CONTACTGROUPALIAS                 133
#define MACRO_CONTACTGROUPMEMBERS               134
#define MACRO_CONTACTGROUPNAMES                 135
#define MACRO_NOTIFICATIONRECIPIENTS            136
#define MACRO_NOTIFICATIONISESCALATED           137
#define MACRO_NOTIFICATIONAUTHOR                138
#define MACRO_NOTIFICATIONAUTHORNAME            139
#define MACRO_NOTIFICATIONAUTHORALIAS           140
#define MACRO_NOTIFICATIONCOMMENT               141
#define MACRO_EVENTSTARTTIME                    142
#define MACRO_HOSTPROBLEMID                     143
#define MACRO_LASTHOSTPROBLEMID                 144
#define MACRO_SERVICEPROBLEMID                  145
#define MACRO_LASTSERVICEPROBLEMID              146
#define MACRO_ISVALIDTIME                       147
#define MACRO_NEXTVALIDTIME                     148
#define MACRO_LASTHOSTSTATE                     149
#define MACRO_LASTHOSTSTATEID                   150
#define MACRO_LASTSERVICESTATE                  151
#define MACRO_LASTSERVICESTATEID                152



/************* MACRO CLEANING OPTIONS *****************/

#define STRIP_ILLEGAL_MACRO_CHARS       1
#define ESCAPE_MACRO_CHARS              2
#define URL_ENCODE_MACRO_CHARS		4



/****************** MACRO FUNCTIONS ******************/

int process_macros(char *,char **,int);             	/* replace macros with their actual values */
char *clean_macro_chars(char *,int);                    /* cleans macros characters before insertion into output string */

int grab_service_macros(service *);                  	/* updates the service macro data */
int grab_host_macros(host *);                        	/* updates the host macro data */
int grab_servicegroup_macros(servicegroup *);           /* updates servicegroup macros */
int grab_hostgroup_macros(hostgroup *);                 /* updates hostgroup macros */
int grab_contact_macros(contact *);                  	/* updates the contact macro data */
int grab_contactgroup_macros(contactgroup *);           /* updates contactgroup macros */
int grab_datetime_macros(void);				/* updates date/time macros */
int grab_on_demand_macro(char *);                       /* fetches an on-demand macro */

char *get_url_encoded_string(char *);			/* URL encode a string */

int init_macros(void);
int init_macrox_names(void);
int add_macrox_name(int,char *);
int free_macrox_names(void);

int clear_argv_macros(void);
int clear_volatile_macros(void);
int clear_host_macros(void);
int clear_service_macros(void);
int clear_hostgroup_macros(void);
int clear_servicegroup_macros(void);
int clear_contact_macros(void);
int clear_contactgroup_macros(void);
int clear_summary_macros(void);

int grab_macro_value(char *,char **,int *,int *);
int grab_macrox_value(int,char *,char *,char **,int *);
int grab_custom_macro_value(char *,char *,char *,char **);
int grab_datetime_macro(int,char *,char *,char **);
int grab_standard_host_macro(int,host *,char **,int *);
int grab_standard_hostgroup_macro(int,hostgroup *,char **);
int grab_standard_service_macro(int,service *,char **,int *);
int grab_standard_servicegroup_macro(int,servicegroup *,char **);
int grab_standard_contact_macro(int,contact *,char **);
int grab_contact_address_macro(int,contact *,char **);
int grab_standard_contactgroup_macro(int,contactgroup *,char **);
int grab_custom_object_macro(char *,customvariablesmember *,char **);


#ifdef NSCORE
int set_all_macro_environment_vars(int);
int set_macrox_environment_vars(int);
int set_argv_macro_environment_vars(int);
int set_custom_macro_environment_vars(int);
int set_contact_address_environment_vars(int);
int set_macro_environment_var(char *,char *,int);
#endif

#endif
