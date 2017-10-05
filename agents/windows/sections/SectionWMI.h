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

#ifndef SectionWMI_h
#define SectionWMI_h

#include <memory>
#include <string>
#include <vector>
#include "../wmiHelper.h"
#undef CreateMutex
#include "../Section.h"

class SectionWMI : public Section {
    std::wstring _namespace{L"Root\\cimv2"};
    std::wstring _object;
    std::vector<std::wstring> _columns;
    bool _toggle_if_missing{false};
    time_t _disabled_until{0};

    std::unique_ptr<wmi::Helper> _helper;

public:
    SectionWMI(const std::string &outputName, const std::string &configName,
               const Environment &env, Logger *logger,
               const WinApiAdaptor &winapi);

    SectionWMI *withNamespace(const wchar_t *name);
    SectionWMI *withObject(const wchar_t *path);
    SectionWMI *withColumns(const std::vector<std::wstring> &columns);
    SectionWMI *withToggleIfMissing();

protected:
    void suspend(int duration);

    virtual bool produceOutputInner(std::ostream &out) override;

private:
    void outputTable(std::ostream &out, wmi::Result &data);
};

#endif  // SectionWMI_h
