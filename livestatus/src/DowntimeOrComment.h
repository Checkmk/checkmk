// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef DowntimeOrComment_h
#define DowntimeOrComment_h

#include "config.h"  // IWYU pragma: keep

#include <chrono>
#include <string>

#include "nagios.h"

class Downtime {
public:
    int _type;
    bool _is_service;
    host *_host;
    service *_service;
    std::chrono::system_clock::time_point _entry_time;
    std::string _author_name;
    std::string _comment;
    unsigned long _id;
    std::chrono::system_clock::time_point _start_time;
    std::chrono::system_clock::time_point _end_time;
    int _fixed;
    std::chrono::nanoseconds _duration;
    unsigned long _triggered_by;
};

class Comment {
public:
    int _type;
    bool _is_service;
    host *_host;
    service *_service;
    std::chrono::system_clock::time_point _entry_time;
    std::string _author_name;
    std::string _comment;
    unsigned long _id;
    std::chrono::system_clock::time_point _expire_time;
    int _persistent;
    int _source;
    int _entry_type;
    int _expires;
};

#endif  // DowntimeOrComment_h
