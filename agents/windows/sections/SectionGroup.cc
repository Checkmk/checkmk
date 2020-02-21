// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#include "SectionGroup.h"

#include "Logger.h"
#include "SectionHeader.h"

namespace section_group {
constexpr const char kSeparator = kPipeSeparator;

std::unique_ptr<SectionHeaderBase> makeHeader(bool show_header,
                                              const std::string &outputName,
                                              Logger *logger) {
    if (show_header)
        return std::make_unique<SectionHeader<kSeparator, SectionBrackets>>(
            outputName, logger);
    else
        return std::make_unique<HiddenHeader>(logger);
}

}  // namespace section_group

SectionGroup::SectionGroup(const std::string &outputName,
                           const std::string &configName,
                           const Environment &env, Logger *logger,
                           const WinApiInterface &winapi, bool show_header)
    : Section(configName, env, logger, winapi,
              section_group::makeHeader(show_header, outputName, logger)) {}

SectionGroup *SectionGroup::withSubSection(Section *section) {
    _subsections.push_back(std::unique_ptr<Section>(section));
    return this;
}

SectionGroup *SectionGroup::withDependentSubSection(Section *section) {
    _dependent_subsections.push_back(std::unique_ptr<Section>(section));
    return this;
}

SectionGroup *SectionGroup::withToggleIfMissing() {
    _toggle_if_missing = true;
    return this;
}

bool SectionGroup::produceOutputInner(
    std::ostream &out, const std::optional<std::string> &remoteIP) {
    Debug(_logger) << "SectionGroup::produceOutputInner";
    time_t now = time(nullptr);
    if (_disabled_until > now) {
        return false;
    }

    bool all_failed = true;

    for (const auto &table : _subsections) {
        if (table->produceOutput(out, remoteIP)) {
            all_failed = false;
        }
    }

    if (!all_failed) {
        for (const auto &table : _dependent_subsections) {
            if (table->produceOutput(out, remoteIP)) {
                all_failed = false;
            }
        }
    }

    if (_toggle_if_missing && all_failed) {
        _disabled_until = now + 3600;
    }

    return !all_failed;
}
