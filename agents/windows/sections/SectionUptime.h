// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#ifndef SectionUptime_h
#define SectionUptime_h

#include <map>
#include <memory>
#include <string>
#include <vector>
#include "Section.h"
#include "wmiHelper.h"

class Environment;

class SectionUptime : public Section {
    using GetTickCount64_type = ULONGLONG(WINAPI *)(void);

public:
    SectionUptime(const Environment &env, Logger *logger,
                  const WinApiInterface &winapi);

protected:
    virtual bool produceOutputInner(
        std::ostream &out, const std::optional<std::string> &) override;

private:
    std::string outputTickCount64();
    std::string outputWMI();

    GetTickCount64_type GetTickCount64_dyn{nullptr};
    std::unique_ptr<wmi::Helper> _wmi_helper;
};

#endif  // SectionUptime_h
