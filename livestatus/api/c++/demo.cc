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
	while (0 != (row = live.readLine()))
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

