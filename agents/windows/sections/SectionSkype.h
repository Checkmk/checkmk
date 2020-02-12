// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#ifndef SectionSkype_h
#define SectionSkype_h

#include "Section.h"
#include "SectionGroup.h"
#include "SectionPerfcounter.h"

class SectionSkype : public SectionGroup {
public:
    SectionSkype(const Environment &env, Logger *logger,
                 const WinApiInterface &winapi);

protected:
    virtual bool produceOutputInner(
        std::ostream &out, const std::optional<std::string> &remoteIP) override;

private:
    // Use a single counter name -> base no. map. Fill lazily when first needed.
    NameBaseNumberMap _nameNumberMap;
};

#endif  // SectionSkype_h
