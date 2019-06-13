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

#include "SectionWMI.h"

#include <algorithm>
#include <ctime>
#include "Logger.h"
#include "SectionHeader.h"
#include "stringutil.h"
#include "wmiHelper.h"

#if !defined(SUCCEEDED)
#define SUCCEEDED(hr) ((HRESULT)(hr) >= 0)
#endif

// How to fix broken performance counters
// http://johansenreidar.blogspot.de/2014/01/windows-server-rebuild-all-performance.html

namespace wmi {
constexpr const char kSeparator = kTabSeparator;
constexpr const wchar_t *kWideSeparator = kWideTabSeparator;

std::unique_ptr<SectionHeaderBase> makeHeader(bool subSection,
                                              const std::string &outputName,
                                              Logger *logger) {
    if (subSection)
        return std::make_unique<SubSectionHeader>(outputName, logger);
    else
        return std::make_unique<
            SectionHeader<wmi::kSeparator, SectionBrackets>>(outputName,
                                                             logger);
}

}  // namespace wmi

SectionWMI::SectionWMI(const std::string &outputName,
                       const std::string &configName, const Environment &env,
                       Logger *logger, const WinApiInterface &winapi,
                       bool asSubSection /*= false*/)
    : Section(configName, env, logger, winapi,
              wmi::makeHeader(asSubSection, outputName, logger)) {}

SectionWMI *SectionWMI::withNamespace(const wchar_t *name) {
    _namespace = name;
    return this;
}

SectionWMI *SectionWMI::withObject(const wchar_t *path) {
    _object = path;
    return this;
}

SectionWMI *SectionWMI::withColumns(const std::vector<std::wstring> &columns) {
    _columns = columns;
    return this;
}

SectionWMI *SectionWMI::withToggleIfMissing() {
    _toggle_if_missing = true;
    return this;
}

void SectionWMI::outputTable(std::ostream &out, wmi::Result &data) {
    // output header
    if (!data.valid()) {
        return;
    }

    // First use a local stream buffer...
    std::stringstream localStream;
    localStream << Utf8(join(data.names(), wmi::kWideSeparator)) << "\n";

    // output data
    bool more = true;
    while (more) {
        std::vector<std::wstring> values = data.names();
        // resolve all table keys to their value on this row.
        std::transform(values.begin(), values.end(), values.begin(),
                       [&data](const std::wstring &name) {
                           return data.get<std::wstring>(name.c_str());
                       });
        localStream << Utf8(join(values, wmi::kWideSeparator));

        more = data.next();

        if (more) {
            localStream << "\n";
        }
    }

    // ...and output local stream buffer only when no WMI timeout was thrown.
    out << localStream.rdbuf();
}

void SectionWMI::suspend(int duration) {
    _disabled_until = time(nullptr) + duration;
}

// ********************************************************
// copy pasted from the new agent, unit-tested in new Agent
// ********************************************************
namespace cma::tools {
inline std::vector<std::string> SplitString(const std::string &In,
                                            const std::string Delim,
                                            int MaxCount = 0) noexcept {
    // sanity
    if (In.empty()) return {};
    if (Delim.empty()) return {In};

    size_t start = 0U;
    std::vector<std::string> result;

    auto end = In.find(Delim);
    while (end != std::string::npos) {
        result.push_back(In.substr(start, end - start));

        start = end + Delim.length();
        end = In.find(Delim, start);

        // check for a skipping rest
        if (result.size() == static_cast<size_t>(MaxCount)) {
            end = std::string::npos;
            break;
        }
    }

    auto last_string = In.substr(start, end);
    if (!last_string.empty()) result.push_back(last_string);

    return result;
}
}  // namespace cma::tools

// ********************************************************
// copy pasted from the new agent, unit-tested in new Agent
// ********************************************************
// adds to the output Table from the WMI WMIStatus column
// column value is either Timeout or OK
// Before
// Name,Freq
// Total,1500
// AFter
// Name,Freq,WMIStatus
// Total,1500,OK
// Empty or quite short strings are replaced empty string
std::string WmiPostProcess(const std::string &In, bool ExceptionOn,
                           char Separator) {
    if (In.size() < 5) {  // 5 is meaningless, just anything low
        // data absent
        return ExceptionOn ? std::string() : In;
    }

    std::string tail_0;
    tail_0 += Separator;
    tail_0 += "WMIStatus\n";

    std::string tail_other;
    tail_other += Separator;
    tail_other += ExceptionOn ? "Timeout\n" : "OK\n";

    auto table = cma::tools::SplitString(In, "\n");
    size_t s_required = 0;
    table[0] += tail_0;
    s_required += table[0].size();
    for (size_t i = 1; i < table.size(); ++i) {
        table[i] += tail_other;
        s_required += table[i].size();
    }

    std::string out;
    out.reserve(s_required);
    for (const auto line : table) {
        out += line;
    }
    return out;
}

bool SectionWMI::produceOutputInner(std::ostream &Out,
                                    const std::optional<std::string> &) {
    Debug(_logger) << "SectionWMI::produceOutputInner";

    if (_disabled_until > time(nullptr)) {
        return false;
    }

    bool success = true;

    bool exception_on = false;

    try {
        if (_helper.get() == nullptr) {
            _helper.reset(
                new wmi::Helper(_logger, _winapi, _namespace.c_str()));
        }

        wmi::Result result(_logger, _winapi);

        if (_columns.empty()) {
            // no columns set, return everything
            result = _helper->getClass(_object.c_str());
        } else {
            std::wstringstream query;
            query << L"SELECT " << join(_columns, wmi::kWideSeparator)
                  << L" FROM " << _object;
            result = _helper->query(query.str().c_str());
        }

        success = result.valid() || SUCCEEDED(result.last_error());

        if (_toggle_if_missing && !success) {
            // in the past, wmi tables were toggled permanently if they were
            // missing,
            // but testing occasionally shouldn't hurt.
            suspend(3600);
        }

        std::stringstream out;
        outputTable(out, result);
        cached_ = out.str();
    } catch (const wmi::Timeout &t) {
        exception_on = true;
        // only logging
        if (cached_.size()) {
            Debug(_logger) << "SectionWMI::produceOutputInner caught "
                           << t.what() << " cached data reused";
        } else {
            Debug(_logger) << "SectionWMI::produceOutputInner caught "
                           << t.what();
        }
        success = true;
    }

    // in cache we always have last valid data. Or nothing.
    // those cached data should be decorated with new column
    auto modified = WmiPostProcess(cached_, exception_on, wmi::kSeparator);
    if (modified.size()) Out << modified;

    return success;
}
