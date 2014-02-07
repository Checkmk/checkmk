/*****************************************************************************
 *
 * CGIAUTH.H - Authorization utilities header file
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

#ifndef _AUTH_H
#define _AUTH_H
#include "common.h"
#include "objects.h"

NAGIOS_BEGIN_DECL

typedef struct authdata_struct {
	char *username;
	int authorized_for_all_hosts;
	int authorized_for_all_host_commands;
	int authorized_for_all_services;
	int authorized_for_all_service_commands;
	int authorized_for_system_information;
	int authorized_for_system_commands;
	int authorized_for_configuration_information;
	int authorized_for_read_only;
	int authenticated;
	} authdata;



int get_authentication_information(authdata *);       /* gets current authentication information */

int is_authorized_for_host(host *, authdata *);
int is_authorized_for_service(service *, authdata *);

int is_authorized_for_all_hosts(authdata *);
int is_authorized_for_all_services(authdata *);

int is_authorized_for_system_information(authdata *);
int is_authorized_for_system_commands(authdata *);
int is_authorized_for_host_commands(host *, authdata *);
int is_authorized_for_service_commands(service *, authdata *);

int is_authorized_for_hostgroup(hostgroup *, authdata *);
int is_authorized_for_servicegroup(servicegroup *, authdata *);

int is_authorized_for_hostgroup_commands(hostgroup *, authdata *);
int is_authorized_for_servicegroup_commands(servicegroup *, authdata *);

int is_authorized_for_configuration_information(authdata *);

int is_authorized_for_read_only(authdata *);

NAGIOS_END_DECL

#endif
