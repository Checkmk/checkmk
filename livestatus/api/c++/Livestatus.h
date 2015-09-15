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

#ifndef Livestatus_h
#define Livestatus_h

#include <stdio.h>
#include <vector>
#include <string>

// simple C++ API for accessing Livestatus from C++,
// currently supports only UNIX sockets, no TCP. But
// this is only a simple enhancement.

class Livestatus
{
    int _connection;
    FILE *_file;

public:
    Livestatus() : _connection(-1), _file(0) {};
    ~Livestatus();
    void connectUNIX(const char *socketpath);
    bool isConnected() const { return _connection >= 0; };
    void disconnect();
    void sendQuery(const char *query);
    std::vector<std::string> *nextRow();
};



#endif // Livestatus_h

