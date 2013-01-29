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

#include <stdio.h>
#include "Livestatus.h"

const char *query = "GET status\nColumns: livestatus_version program_version\nColumnHeaders: on\n";
#define MAX_LINE_SIZE 8192

int main(int argc, char **argv)
{
    if (argc != 2) {
	fprintf(stderr, "Usage: %s SOCKETPATH\n", argv[0]);
	return 1;
    }

    const char *socket_path = argv[1];
    Livestatus live;
    live.connectUNIX(socket_path);
    if (live.isConnected()) {
	live.sendQuery(query);
	std::vector<std::string> *row;
	while (0 != (row = live.nextRow()))
	{
	    printf("Line:\n");
	    for (int i=0; i<row->size(); i++) 
		printf("%s\n", (*row)[i].c_str());
	    delete row;
	}
	live.disconnect();
    }
    else {
	fprintf(stderr, "Couldn't connect to socket '%s'\n", socket_path);
	return 1;
    }
    return 0;
}

