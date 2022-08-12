/*****************************************************************************
 *
 * PERFDATA.H - Include file for performance data routines
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

#ifndef _PERFDATA_H
#define _PERFDATA_H

#include "objects.h"

#ifdef __cplusplus
  extern "C" {
#endif

int initialize_performance_data(char *);	                /* initializes performance data */
int cleanup_performance_data(char *);                           /* cleans up performance data */

int update_host_performance_data(host *);       	        /* updates host performance data */
int update_service_performance_data(service *);         	/* updates service performance data */

#ifdef __cplusplus
  }
#endif

#endif
