// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#ifndef SectionWMI_h
#define SectionWMI_h

#include <memory>
#include <string>
#include <vector>
#include "Section.h"
#include "wmiHelper.h"

class SectionWMI : public Section {
public:
    SectionWMI(const std::string &outputName, const std::string &configName,
               const Environment &env, Logger *logger,
               const WinApiInterface &winapi, bool asSubSection = false);

    SectionWMI *withNamespace(const wchar_t *name);
    SectionWMI *withObject(const wchar_t *path);
    SectionWMI *withColumns(const std::vector<std::wstring> &columns);
    SectionWMI *withToggleIfMissing();

protected:
    void suspend(int duration);

    virtual bool produceOutputInner(
        std::ostream &out, const std::optional<std::string> &) override;

private:
    void outputTable(std::ostream &out, wmi::Result &data);

    std::wstring _namespace{L"Root\\cimv2"};
    std::wstring _object;
    std::vector<std::wstring> _columns;
    bool _toggle_if_missing{false};
    time_t _disabled_until{0};
    std::unique_ptr<wmi::Helper> _helper;

    std::string cached_;  // last output stored here, may be reused on timeout
};

#endif  // SectionWMI_h
