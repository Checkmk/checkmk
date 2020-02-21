// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#ifndef SectionWinperf_h
#define SectionWinperf_h

#include <memory>
#include <string>
#include <vector>
#include "Section.h"

namespace wmi {
class Helper;
class Result;
}  // namespace wmi

class SectionWinperf : public Section {
public:
    SectionWinperf(const std::string &name, const Environment &env,
                   Logger *logger, const WinApiInterface &winapi);

    SectionWinperf *withBase(unsigned int base);

protected:
    virtual bool produceOutputInner(
        std::ostream &out, const std::optional<std::string> &) override;

private:
    unsigned long _base;
};

#endif  // SectionWinperf_h
