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
#include "../stringutil.h"
#include "../wmiHelper.h"

#define SUCCEEDED(hr) ((HRESULT)(hr) >= 0)

// How to fix broken performance counters
// http://johansenreidar.blogspot.de/2014/01/windows-server-rebuild-all-performance.html

SectionWMI::SectionWMI(const std::string &outputName,
                       const std::string &configName, const Environment &env,
                       Logger *logger, const WinApiAdaptor &winapi)
    : Section(outputName, configName, env, logger, winapi) {
    withSeparator(',');
}

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
    out << Utf8(join(data.names(), L",")) << "\n";

    // output data
    bool more = true;
    while (more) {
        std::vector<std::wstring> values = data.names();
        // resolve all table keys to their value on this row.
        std::transform(values.begin(), values.end(), values.begin(),
                       [&data](const std::wstring &name) {
                           return data.get<std::wstring>(name.c_str());
                       });
        out << Utf8(join(values, L","));

        more = data.next();
        if (more) {
            out << "\n";
        }
    }
}

void SectionWMI::suspend(int duration) {
    _disabled_until = time(nullptr) + duration;
}

bool SectionWMI::produceOutputInner(std::ostream &out) {
    if (_disabled_until > time(nullptr)) {
        return false;
    }

    if (_helper.get() == nullptr) {
        _helper.reset(new wmi::Helper(_winapi, _namespace.c_str()));
    }

    wmi::Result result(_winapi);

    if (_columns.empty()) {
        // no columns set, return everything
        result = _helper->getClass(_object.c_str());
    } else {
        std::wstringstream query;
        query << L"SELECT " << join(_columns, L",") << L" FROM " << _object;
        result = _helper->query(query.str().c_str());
    }

    bool success = result.valid() || SUCCEEDED(result.last_error());

    if (_toggle_if_missing && !success) {
        // in the past, wmi tables were toggled permanently if they were
        // missing,
        // but testing occasionally shouldn't hurt.
        suspend(3600);
    }

    outputTable(out, result);

    return success;
}
