// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#ifndef SectionSystemtime_h
#define SectionSystemtime_h

#include "Section.h"

class SectionSystemtime : public Section {
public:
    SectionSystemtime(const Environment &env, Logger *logger,
                      const WinApiInterface &winapi);

protected:
    virtual bool produceOutputInner(
        std::ostream &out, const std::optional<std::string> &) override;
};

#endif  // SectionSystemtime_h
