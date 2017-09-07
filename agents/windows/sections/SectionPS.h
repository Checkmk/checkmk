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

#ifndef SectionPS_h
#define SectionPS_h

#include <map>
#include <memory>
#include <string>
#include <vector>
#include "../Configurable.h"
#include "../Section.h"
#include "../wmiHelper.h"

class SectionPS : public Section {
    Configurable<bool> _use_wmi;
    Configurable<bool> _full_commandline;

    std::unique_ptr<wmi::Helper> _helper;

public:
    SectionPS(Configuration &config, Logger *logger,
              const WinApiAdaptor &winapi);

protected:
    virtual bool produceOutputInner(std::ostream &out) override;

private:
    bool ExtractProcessOwner(HANDLE hProcess_i, std::string &csOwner_o);

    struct process_entry {
        unsigned long long process_id;
        unsigned long long working_set_size;
        unsigned long long pagefile_usage;
        unsigned long long virtual_size;
    };

    typedef std::map<unsigned long long, process_entry> process_entry_t;

    process_entry_t getProcessPerfdata();

    void outputProcess(std::ostream &out, ULONGLONG virtual_size,
                       ULONGLONG working_set_size, ULONGLONG pagefile_usage,
                       ULONGLONG uptime, ULONGLONG usermode_time,
                       ULONGLONG kernelmode_time, DWORD process_id,
                       DWORD process_handle_count, DWORD thread_count,
                       const std::string &user, LPCSTR exe_file);

    bool outputWMI(std::ostream &out);
    bool outputNative(std::ostream &out);
};

#endif  // SectionPS_h
