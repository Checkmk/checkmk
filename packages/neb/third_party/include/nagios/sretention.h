/*****************************************************************************
 *
 * SRETENTION.H - Header for state retention routines
 *
 * Copyright (c) 1999-2006 Ethan Galstad (egalstad@nagios.org)
 * Last Modified:   02-28-2006
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

#ifdef __cplusplus
  extern "C" {
#endif

int initialize_retention_data(char *);
int cleanup_retention_data(char *);
int save_state_information(int);                 /* saves all host and state information */
int read_initial_state_information(void);        /* reads in initial host and state information */

#ifdef __cplusplus
  }
#endif
