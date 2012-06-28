// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2012             mk@mathias-kettner.de |
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

#ifndef TableStateHistory_h
#define TableStateHistory_h

#include <map>
#include <time.h>
#include "config.h"
#include "Table.h"
#include "string.h"

class Logfile;


class HostServiceKey{
public:
	HostServiceKey(const std::string &host, const std::string &service){
		host_name = host;
		service_name = service;
	}
	std::string host_name;
	std::string service_name;
	bool operator<(const HostServiceKey& other) const{
		return (strcmp(other.host_name.c_str(), host_name.c_str()) < 0);
	}
};

class HostServiceState{
public:
	time_t  from;
	time_t  until;
	time_t  duration;
	int     attempt;
	bool    hard_state; // true: hard, false: soft
	char    state;
	bool    in_downtime;
	bool    in_notification_period;
	//int*    log_ptr;
	// int tp_state
	// bool acknowledged
};

typedef map<HostServiceKey, HostServiceState> SLA_Info;

class TableStateHistory : public Table
{

public:
    TableStateHistory();
    ~TableStateHistory();
    const char *name() { return "log"; }
    const char *prefixname() { return "logs"; }
    bool isAuthorized(contact *ctc, void *data);
    void handleNewMessage(Logfile *logfile, time_t since, time_t until, unsigned logclasses);
    void answerQuery(Query *query);
    Column *column(const char *colname); // override in order to handle current_

private:
   bool answerQuery(Query *, Logfile *, time_t, time_t);
   SLA_Info* sla_info;
};

#endif // TableStateHistory_h
