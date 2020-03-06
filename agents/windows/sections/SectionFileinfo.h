// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#ifndef SectionFileinfo_h
#define SectionFileinfo_h

#include <experimental/filesystem>
#include "Configurable.h"
#include "Section.h"

namespace fs = std::experimental::filesystem;
using PathsT = std::vector<fs::path>;

class Configuration;

class SectionFileinfo : public Section {
public:
    SectionFileinfo(Configuration &config, Logger *logger,
                    const WinApiInterface &winapi);

protected:
    virtual bool produceOutputInner(
        std::ostream &out, const std::optional<std::string> &) override;

private:
    ListConfigurable<PathsT, BlockMode::Nop<PathsT>,
                     AddMode::PriorityAppend<PathsT>>
        _fileinfo_paths;
};

#endif  // SectionFileinfo_h
