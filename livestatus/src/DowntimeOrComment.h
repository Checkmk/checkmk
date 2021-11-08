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

/* The structs for downtime and comment are so similar, that
   we handle them with the same logic */

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

   typedef struct nebstruct_comment_struct{
   int             type;
   int             flags;
   int             attr;
   struct timeval  timestamp;

   int             comment_type;
   char            *host_name;
   char            *service_description;
   time_t          entry_time;
   char            *author_name;
   char            *comment_data;
   int             persistent;
   int             source;
   int             entry_type;
   int             expires;
   time_t          expire_time;
   unsigned long   comment_id;

   void            *object_ptr; // not implemented yet
   }nebstruct_comment_data;
 */

class DowntimeOrComment {
public:
    int _type;
    bool _is_service;
    host *_host;
    service *_service;
    std::chrono::system_clock::time_point _entry_time;
    std::string _author_name;
    std::string _comment;
    unsigned long _id;

    virtual ~DowntimeOrComment() = default;

protected:
    DowntimeOrComment(host *hst, service *svc, nebstruct_downtime_struct *dt,
                      unsigned long id);
};

class Downtime : public DowntimeOrComment {
public:
    std::chrono::system_clock::time_point _start_time;
    std::chrono::system_clock::time_point _end_time;
    int _fixed;
    std::chrono::seconds _duration;
    unsigned long _triggered_by;
    Downtime(host *hst, service *svc, nebstruct_downtime_struct *dt);
};

class Comment : public DowntimeOrComment {
public:
    std::chrono::system_clock::time_point _expire_time;
    int _persistent;
    int _source;
    int _entry_type;
    int _expires;
    Comment(host *hst, service *svc, nebstruct_comment_struct *co);
};

#endif  // DowntimeOrComment_h
