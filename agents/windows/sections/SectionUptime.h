// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2017             mk@mathias-kettner.de |
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

#ifndef SectionUptime_h
#define SectionUptime_h

#include <map>
#include <memory>
#include <string>
#include <vector>
#include "../wmiHelper.h"
#undef CreateMutex
#include "../Section.h"

class Environment;

class SectionUptime : public Section {
    typedef ULONGLONG WINAPI (*GetTickCount64_type)(void);
    GetTickCount64_type GetTickCount64_dyn{nullptr};

    std::unique_ptr<wmi::Helper> _wmi_helper;

public:
    SectionUptime(const Environment &env, LoggerAdaptor &logger,
                  const WinApiAdaptor &winapi);

protected:
    virtual bool produceOutputInner(std::ostream &out) override;

private:
    std::string outputTickCount64();
    std::string outputWMI();
};

#endif  // SectionUptime_h
