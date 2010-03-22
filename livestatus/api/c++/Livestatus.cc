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


std::vector<std::string> *Livestatus::readLine()
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

