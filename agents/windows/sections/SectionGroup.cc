// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2017             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include "SectionGroup.h"
#include "Logger.h"
#include "SectionHeader.h"

namespace section_group {
constexpr const char kSeparator = kTabSeparator;

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
