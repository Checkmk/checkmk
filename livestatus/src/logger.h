// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#ifndef logger_h
#define logger_h

#include "config.h"

#ifdef CMC
#include <syslog.h>
#define LG_DEBUG LOG_INFO
#define LG_INFO  LOG_NOTICE
#define LG_WARN  LOG_WARNING
#define LG_ERR   LOG_ERR
#define LG_CRIT  LOG_CRIT
#define LG_ALERT LOG_ALERT
#else
// TODO: Really use log levels
#define LG_INFO 262144
#define LG_WARN  LOG_INFO
#define LG_ERR   LOG_INFO
#define LG_CRIT  LOG_INFO
#define LG_DEBUG LOG_INFO
#define LG_ALERT LOG_INFO
#endif

#ifdef __cplusplus
#ifndef CMC
extern "C" {
#endif
#endif

void logger(int priority, const char *loginfo, ...);
void open_logfile();
void close_logfile();

#ifdef __cplusplus
#ifndef CMC
}
#endif
#endif

#endif // logger_h

