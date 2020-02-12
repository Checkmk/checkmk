// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#ifndef SectionPS_h
#define SectionPS_h

#include <map>
#include <memory>
#include <string>
#include <vector>
#include "Configurable.h"
#include "Section.h"
#include "wmiHelper.h"

class SectionPS : public Section {
    using NullHandle = WrappedHandle<NullHandleTraits>;
    using WinHandle = WrappedHandle<InvalidHandleTraits>;

    struct process_entry {
        unsigned long long process_id;
        unsigned long long working_set_size;
        unsigned long long pagefile_usage;
        unsigned long long virtual_size;
    };

    using process_entry_t = std::map<unsigned long long, process_entry>;

public:
    SectionPS(Configuration &config, Logger *logger,
              const WinApiInterface &winapi);

protected:
    virtual bool produceOutputInner(
        std::ostream &out, const std::optional<std::string> &) override;

private:
    bool ExtractProcessOwner(const NullHandle &hProcess_i,
                             std::string &csOwner_o);
    process_entry_t getProcessPerfdata();
    void outputProcess(std::ostream &out, ULONGLONG virtual_size,
                       ULONGLONG working_set_size, long long pagefile_usage,
                       ULONGLONG uptime, long long usermode_time,
                       long long kernelmode_time, long long process_id,
                       long long process_handle_count, long long thread_count,
                       const std::string &user, const std::string &exe_file);
    bool outputWMI(std::ostream &out);
    bool outputNative(std::ostream &out);

    Configurable<bool> _use_wmi;
    Configurable<bool> _full_commandline;
    std::unique_ptr<wmi::Helper> _helper;
};

#endif  // SectionPS_h
