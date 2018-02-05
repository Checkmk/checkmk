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
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// tails. You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#ifndef waittriggers_h
#define waittriggers_h

#include "config.h"  // IWYU pragma: keep
#include <chrono>
#include <condition_variable>
#include <mutex>
#include <string>

std::mutex &trigger_mutex();
std::condition_variable &trigger_all();
std::condition_variable &trigger_check();
std::condition_variable &trigger_state();
std::condition_variable &trigger_log();
std::condition_variable &trigger_downtime();
std::condition_variable &trigger_comment();
std::condition_variable &trigger_command();
std::condition_variable &trigger_program();

std::condition_variable &trigger_find(const std::string &name);

void trigger_notify_all(std::condition_variable &cond);

void trigger_wait(std::condition_variable &cond);
std::cv_status trigger_wait_for(std::condition_variable &cond,
                                std::chrono::milliseconds ms);

#endif  // waittriggers_h
