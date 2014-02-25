/* include/config.h.  Generated from config.h.in by configure.  */
/************************************************************************
 *
 * Nagios Config Header File
 * Written By: Ethan Galstad (egalstad@nagios.org)
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


/***** NAGIOS STUFF *****/

#define DEFAULT_NAGIOS_USER "nagios"
#define DEFAULT_NAGIOS_GROUP "nagios"

/* stop gcc from bitching about implicit asprintf declarations */
#define _GNU_SOURCE 1

/* Event broker integration */
#define USE_EVENT_BROKER /**/

/* commands used by CGIs */
#define TRACEROUTE_COMMAND "/usr/sbin/traceroute"
/* #undef PING_COMMAND */
/* #undef PING_PACKETS_FIRST */

/* Debugging options */
/* function entry and exit */
/* #undef DEBUG0 */
/* general info messages */
/* #undef DEBUG1 */
/* warning messages */
/* #undef DEBUG2 */
/* service and host checks, other events */
/* #undef DEBUG3 */
/* service and host notifications */
/* #undef DEBUG4 */
/* SQL queries (defunct) */
/* #undef DEBUG5 */

/* I/O implementations */
/* #undef USE_XSDDEFAULT */
/* #undef USE_XCDDEFAULT */
/* #undef USE_XRDDEFAULT */
/* #undef USE_XODTEMPLATE */
/* #undef USE_XPDDEFAULT */
/* #undef USE_XDDDEFAULT */


/***** CGI COMPILE OPTIONS *****/
/* should we compile and use the statusmap CGI? */
/* #undef USE_STATUSMAP */
/* should we compile and use the statuswrl CGI? */
#define USE_STATUSWRL /**/
/* should we compile and use the trends CGI? */
/* #undef USE_TRENDS */
/* should we compile and use the histogram CGI? */
/* #undef USE_HISTOGRAM */



/***** FUNCTION DEFINITIONS *****/

#define HAVE_SETENV 1
#define HAVE_UNSETENV 1
/* #undef HAVE_SOCKET */
#define HAVE_STRDUP 1
#define HAVE_STRSTR 1
#define HAVE_STRTOUL 1
#define HAVE_INITGROUPS 1
/* #undef HAVE_GETLOADAVG */
/* #undef HAVE_GDIMAGECREATETRUECOLOR */



/***** ASPRINTF() AND FRIENDS *****/

/* #undef HAVE_VSNPRINTF */
/* #undef HAVE_SNPRINTF */
/* #undef HAVE_ASPRINTF */
/* #undef HAVE_VASPRINTF */
#define HAVE_C99_VSNPRINTF 1
#define HAVE_VA_COPY 1
/* #undef HAVE___VA_COPY */



/***** MISC DEFINITIONS *****/

#define USE_NANOSLEEP /**/
#define STDC_HEADERS 1
#define HAVE_TM_ZONE 1
/* #undef HAVE_TZNAME */
/* #undef USE_PROC */
#define SOCKET_SIZE_TYPE size_t
#define GETGROUPS_T gid_t
#define RETSIGTYPE void



/***** HEADER FILES *****/

#include <stdio.h>
#include <stdlib.h>

/* needed for the time_t structures we use later... */
/* this include must come before sys/resource.h or we can have problems on some OSes */
#define TIME_WITH_SYS_TIME 1
#define HAVE_SYS_TIME_H 1
#if TIME_WITH_SYS_TIME
#include <sys/time.h>
#include <time.h>
#else
#if HAVE_SYS_TIME_H
#include <sys/time.h>
#else
#include <time.h>
#endif
#endif

#define HAVE_SYS_RESOURCE_H 1
#ifdef HAVE_SYS_RESOURCE_H
#include <sys/resource.h>
#endif

#define HAVE_LIMITS_H 1
#ifdef HAVE_LIMITS_H
#include <limits.h>
#endif

#define HAVE_PWD_H 1
#ifdef HAVE_PWD_H
#include <pwd.h>
#endif
 
#define HAVE_GRP_H 1
#ifdef HAVE_GRP_H
#include <grp.h>
#endif

#define HAVE_STRINGS_H 1
#ifdef HAVE_STRINGS_H
#include <strings.h>
#endif

#define HAVE_STRING_H 1
#ifdef HAVE_STRINGS_H
#include <string.h>
#endif

#define HAVE_UNISTD_H 1
#ifdef HAVE_UNISTD_H
#include <unistd.h>
#endif

#define HAVE_SYSLOG_H 1
#ifdef HAVE_SYSLOG_H
#include <syslog.h>
#endif

#define HAVE_SIGNAL_H 1
#ifdef HAVE_SIGNAL_H
#include <signal.h>
#endif

#define HAVE_SYS_STAT_H 1
#ifdef HAVE_SYS_STAT_H
#include <sys/stat.h>
#endif

#define HAVE_SYS_MMAN_H 1
#ifdef HAVE_SYS_MMAN_H
#include <sys/mman.h>
#endif

#define HAVE_FCNTL_H 1
#ifdef HAVE_FCNTL_H
#include <fcntl.h>
#endif

#define HAVE_STDARG_H 1
#ifdef HAVE_STDARG_H
#include <stdarg.h>
#endif

#define HAVE_SYS_TYPES_H 1
#ifdef HAVE_SYS_TYPES_H
#include <sys/types.h>
#endif

#define HAVE_SYS_WAIT_H 1
#ifdef HAVE_SYS_WAIT_H
#include <sys/wait.h>
#endif

#define HAVE_ERRNO_H 1
#ifdef HAVE_ERRNO_H
#include <errno.h>
#endif

#define HAVE_SYS_TIMEB_H 1
#if HAVE_SYS_TIMEB_H
#include <sys/timeb.h>
#endif

#define HAVE_SYS_IPC_H 1
#ifdef HAVE_SYS_IPC_H
#include <sys/ipc.h>
#endif

#define HAVE_SYS_MSG_H 1
#ifdef HAVE_SYS_MSG_H
#include <sys/msg.h>
#endif

#define HAVE_MATH_H 1
#ifdef HAVE_MATH_H
#include <math.h>
#endif

#define HAVE_CTYPE_H 1
#ifdef HAVE_CTYPE_H
#include <ctype.h>
#endif

#define HAVE_DIRENT_H 1
#ifdef HAVE_DIRENT_H
#include <dirent.h>
#endif

#define HAVE_REGEX_H 1
#ifdef HAVE_REGEX_H
#include <regex.h>

#define HAVE_SYS_SOCKET_H 1
#ifdef HAVE_SYS_SOCKET_H
#include <sys/socket.h>
#endif

/* #undef HAVE_SOCKET */
#ifdef HAVE_SOCKET_H
#include <socket.h>
#endif

#define HAVE_NETINET_IN_H 1
#ifdef HAVE_NETINET_IN_H
#include <netinet/in.h>
#endif

#define HAVE_ARPA_INET_H 1
#ifdef HAVE_ARPA_INET_H
#include <arpa/inet.h>
#endif

#define HAVE_NETDB_H 1
#ifdef HAVE_NETDB_H
#include <netdb.h>
#endif

#define HAVE_LIBGEN_H 1
#ifdef HAVE_LIBGEN_H
#include <libgen.h>
#endif

#define HAVE_SYS_UN_H 1
#ifdef HAVE_SYS_UN_H
#include <sys/un.h>
#endif

#define HAVE_SYS_POLL_H 1
#ifdef HAVE_SYS_POLL_H
#include <sys/poll.h>
#endif

#define HAVE_GETOPT_H 1
#ifdef HAVE_GETOPT_H
#include <getopt.h>
#endif

/* #undef HAVE_LINUX_MODULE_H */
#ifdef HAVE_LINUX_MODULE_H
#include <linux/module.h>
#endif

#define HAVE_LOCALE_H 1
#ifdef HAVE_LOCALE_H
#include <locale.h>
#endif

#define HAVE_WCHAR_H 1
#ifdef HAVE_WCHAR_H
#include <wchar.h>
#endif

/* configure script should allow user to override ltdl choice, but this will do for now... */
/* #undef USE_LTDL */
/* #undef HAVE_LTDL_H */
#ifdef HAVE_LTDL_H
#define USE_LTDL
#endif

#ifdef USE_LTDL
#include <ltdl.h>
#else
#define HAVE_DLFCN_H /**/
#ifdef HAVE_DLFCN_H
#include <dlfcn.h>
#endif
#endif


/* moved to end to prevent AIX compiler warnings */
#ifndef RTLD_GLOBAL
#define RTLD_GLOBAL 0
#endif

#ifndef RTLD_NOW
#define RTLD_NOW 0
#endif


/***** MARO DEFINITIONS *****/

/* this needs to come after all system include files, so we don't accidentally attempt to redefine it */
#ifndef WEXITSTATUS
# define WEXITSTATUS(stat_val) ((unsigned)(stat_val) >> 8)
#endif
#ifndef WIFEXITED
# define WIFEXITED(stat_val) (((stat_val) & 255) == 0)
#endif


#endif
