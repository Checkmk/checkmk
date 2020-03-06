// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#ifndef SectionCheckMK_h
#define SectionCheckMK_h

#include "Configurable.h"
#include "Section.h"

class Environment;
using KVPair = std::pair<std::string, std::string>;
using OnlyFromConfigurable =
    SplittingListConfigurable<only_from_t,
                              BlockMode::FileExclusive<only_from_t>>;

class SectionCheckMK : public Section {
public:
    SectionCheckMK(Configuration &config, OnlyFromConfigurable &only_from,
                   script_statistics_t &script_statistics, Logger *logger,
                   const WinApiInterface &winapi);

protected:
    virtual bool produceOutputInner(
        std::ostream &out, const std::optional<std::string> &) override;

private:
    const Configurable<bool> _crash_debug;
    const OnlyFromConfigurable &_only_from;

    // static fields
    const std::vector<KVPair> _info_fields;

    script_statistics_t &_script_statistics;
};

#endif  // SectionCheckMK_h
