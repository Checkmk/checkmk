// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#ifndef SectionSpool_h
#define SectionSpool_h

#include "Section.h"

class SectionSpool : public Section {
public:
    SectionSpool(const Environment &env, Logger *logger,
                 const WinApiInterface &winapi);

protected:
    virtual bool produceOutputInner(
        std::ostream &out, const std::optional<std::string> &) override;
};

#endif  // SectionSpool_h
