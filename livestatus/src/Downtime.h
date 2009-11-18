// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2009             mk@mathias-kettner.de |
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

#ifndef Downtime_h
#define Downtime_h

#include "config.h"

#include "nagios.h"
#include <string>
using namespace std;

/*
typedef struct nebstruct_downtime_struct{
        int             type;
        int             flags;
        int             attr;
        struct timeval  timestamp;

        int             downtime_type;
        char            *host_name;
        char            *service_description;
        time_t          entry_time;
        char            *author_name;
        char            *comment_data;
        time_t          start_time;
        time_t          end_time;
        int             fixed;
        unsigned long   duration;
        unsigned long   triggered_by;
        unsigned long   downtime_id;

        void            *object_ptr; // not implemented yet
        }nebstruct_downtime_data;
*/

struct Downtime
{
   int           _type;
   host         *_host;
   service      *_service;
   time_t        _entry_time;
   char *        _author_name;
   char*         _comment;
   time_t        _start_time;
   time_t        _end_time;
   int           _fixed;
   int           _duration;
   int           _triggered_by;
   unsigned long _downtime_id;

   Downtime(nebstruct_downtime_data *data);
   ~Downtime();
};


#endif // Downtime_h

