/*****************************************************************************
 *
 * PERFDATA.H - Include file for performance data routines
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

#ifndef _PERFDATA_H
#define _PERFDATA_H

#include "common.h"
#include "objects.h"

NAGIOS_BEGIN_DECL

int initialize_performance_data(const char *);    /* initializes performance data */
int cleanup_performance_data(void);               /* cleans up performance data */

int update_host_performance_data(host *);         /* updates host performance data */
int update_service_performance_data(service *);   /* updates service performance data */

NAGIOS_END_DECL
#endif
