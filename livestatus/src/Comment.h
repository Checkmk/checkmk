// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef Comment_h
#define Comment_h

#include "config.h"  // IWYU pragma: keep

#include <chrono>
#include <string>

#include "nagios.h"

class Comment {
public:
    unsigned long _id;
    std::string _author;
    std::string _comment;
    uint32_t _entry_type;
    std::chrono::system_clock::time_point _entry_time;
    // --------------------------------------------------
    int _type;
    bool _is_service;
    host *_host;
    service *_service;
    std::chrono::system_clock::time_point _expire_time;
    int _persistent;
    int _source;
    int _expires;
};

#endif  // Comment_h
