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

#include <sys/types.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <fcntl.h>
#include <unistd.h>
#include "Livestatus.h"

#define SEPARATORS "Separators: 10 1 2 3\n"

void Livestatus::connectUNIX(const char *socket_path)
{
    _connection = socket(PF_LOCAL, SOCK_STREAM, 0);
    struct sockaddr_un sa;
    sa.sun_family = AF_LOCAL;
    strncpy(sa.sun_path, socket_path, sizeof(sa.sun_path));
    if (0 > connect(_connection, (const struct sockaddr *)&sa, sizeof(sockaddr_un))) {
	close(_connection);
	_connection = -1;	
    }
    else 
	_file = fdopen(_connection, "r");
}


Livestatus::~Livestatus()
{
    disconnect();
}

void Livestatus::disconnect()
{
    if (isConnected()) {
	if (_file)
	    fclose(_file);
	else
	    close(_connection);
    }
    _connection = -1;
    _file = 0;
}

void Livestatus::sendQuery(const char *query)
{
    write(_connection, query, strlen(query));
    write(_connection, SEPARATORS, strlen(SEPARATORS));
    shutdown(_connection, SHUT_WR);
}


std::vector<std::string> *Livestatus::nextRow()
{
    char line[65536];
    if (0 != fgets(line, sizeof(line), _file)) {
	// strip trailing linefeed
	char *end = strlen(line) + line;
	if (end > line && *(end-1) == '\n') {
	    *(end-1) = 0;
	    --end;
	}
	std::vector<std::string> *row = new std::vector<std::string>;
	char *scan = line;
	while (scan < end) {
	    char *zero = scan;
	    while (zero < end && *zero != '\001') zero++;
	    *zero = 0;
	    row->push_back(std::string(scan));
	    scan = zero + 1;
	}
	return row;
    }
    else
	return 0;
}

