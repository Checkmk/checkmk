// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#ifndef SectionServices_h
#define SectionServices_h

#include "Section.h"

class SectionServices : public Section {
public:
    SectionServices(const Environment &env, Logger *logger,
                    const WinApiInterface &winapi);

protected:
    virtual bool produceOutputInner(
        std::ostream &out, const std::optional<std::string> &) override;

private:
    const char *serviceStartType(SC_HANDLE scm, LPCWSTR service_name);
};

#endif  // SectionServices_h
