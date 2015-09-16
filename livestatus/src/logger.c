// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// Copyright by Mathias Kettner and Mathias Kettner GmbH.  All rights reserved.
//
// Check_MK is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.
//
// Check_MK is  distributed in the hope that it will be useful, but
// WITHOUT ANY WARRANTY;  without even the implied warranty of
// MERCHANTABILITY  or  FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU General Public License for more details.
//
// You should have  received  a copy of the  GNU  General Public
// License along with Check_MK.  If  not, email to mk@mathias-kettner.de
// or write to the postal address provided at www.mathias-kettner.de

#include "logger.h"
#include "nagios.h"
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <pthread.h>

extern char g_logfile_path[];
pthread_t g_mainthread_id;
FILE *g_logfile = 0;

void open_logfile()
{
    g_logfile = fopen(g_logfile_path, "a");
    g_mainthread_id = pthread_self(); /* needed to determine main thread later */
    if (!g_logfile)
        logger(LG_WARN, "Cannot open logfile %s: %s", g_logfile_path, strerror(errno));
}

void close_logfile()
{
    if (g_logfile) {
        fclose(g_logfile);
        g_logfile = 0;
    }
}

void logger(int priority, const char *loginfo, ...)
{
    va_list ap;
    va_start(ap, loginfo);

    /* Only the main process may use the Nagios log methods */
    if (!g_logfile || g_mainthread_id == pthread_self()) {
        char buffer[8192];
        snprintf(buffer, 20, "livestatus: ");
        vsnprintf(buffer + strlen(buffer),
        sizeof(buffer) - strlen(buffer), loginfo, ap);
        va_end(ap);
        write_to_all_logs(buffer, priority);
    }
    else {
        if (g_logfile) {
            /* write date/time */
            char timestring[64];
            time_t now_t = time(0);
            struct tm now; localtime_r(&now_t, &now);
            strftime(timestring, 64, "%F %T ", &now);
            fputs(timestring, g_logfile);

            /* write log message */
            vfprintf(g_logfile, loginfo, ap);
            fputc('\n', g_logfile);
            fflush(g_logfile);
            va_end(ap);
        }
    }
}

