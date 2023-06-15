/*****************************************************************************
 *
 * NEBMODULES.H - Include file for event broker modules
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

#ifndef _NEBMODULES_H
#define _NEBMODULES_H

#include "common.h"
NAGIOS_BEGIN_DECL

	/***** MODULE VERSION INFORMATION *****/

#define NEB_API_VERSION(x) int __neb_api_version = x;
#define CURRENT_NEB_API_VERSION    4



	/***** MODULE INFORMATION *****/

#define NEBMODULE_MODINFO_NUMITEMS  6
#define NEBMODULE_MODINFO_TITLE     0
#define NEBMODULE_MODINFO_AUTHOR    1
#define NEBMODULE_MODINFO_COPYRIGHT 2
#define NEBMODULE_MODINFO_VERSION   3
#define NEBMODULE_MODINFO_LICENSE   4
#define NEBMODULE_MODINFO_DESC      5



	/***** MODULE LOAD/UNLOAD OPTIONS *****/

#define NEBMODULE_NORMAL_LOAD       0    /* module is being loaded normally */
#define NEBMODULE_REQUEST_UNLOAD    0    /* request module to unload (but don't force it) */
#define NEBMODULE_FORCE_UNLOAD      1    /* force module to unload */



	/***** MODULES UNLOAD REASONS *****/

#define NEBMODULE_NEB_SHUTDOWN      1    /* event broker is shutting down */
#define NEBMODULE_NEB_RESTART       2    /* event broker is restarting */
#define NEBMODULE_ERROR_NO_INIT     3    /* _module_init() function was not found in module */
#define NEBMODULE_ERROR_BAD_INIT    4    /* _module_init() function returned a bad code */
#define NEBMODULE_ERROR_API_VERSION 5    /* module version is incompatible with current api */



/***** MODULE STRUCTURES *****/

/* NEB module structure */
typedef struct nebmodule_struct {
	char            *filename;
	char            *dl_file; /* the file we actually loaded */
	char            *args;
	char            *info[NEBMODULE_MODINFO_NUMITEMS];
	int             should_be_loaded;
	int             is_currently_loaded;
	int             core_module;
#ifdef USE_LTDL
	lt_dlhandle     module_handle;
	lt_ptr          init_func;
	lt_ptr          deinit_func;
#else
	void            *module_handle;
	void            *init_func;
	void            *deinit_func;
#endif
	struct nebmodule_struct *next;
	} nebmodule;


/***** MODULE FUNCTIONS *****/
int neb_set_module_info(void *, int, char *);

NAGIOS_END_DECL
#endif
