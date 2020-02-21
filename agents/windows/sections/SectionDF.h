// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#ifndef SectionDF_h
#define SectionDF_h

#include "Section.h"

class Environment;

class SectionDF : public Section {
public:
    SectionDF(const Environment &env, Logger *logger,
              const WinApiInterface &winapi);

protected:
    virtual bool produceOutputInner(
        std::ostream &out, const std::optional<std::string> &) override;

private:
    void output_filesystem(std::ostream &out, const std::string &volid);
    void output_mountpoints(std::ostream &out, const std::string &volid);
};

#endif  // SectionDF_h
