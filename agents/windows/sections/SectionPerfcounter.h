// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#ifndef SectionPerfcounter_h
#define SectionPerfcounter_h

#include <memory>
#include <string>
#include <unordered_map>
#include <vector>
#include "Section.h"

class NameBaseNumberMap {
public:
    NameBaseNumberMap(Logger *logger, const WinApiInterface &winapi)
        : _logger(logger), _winapi(winapi) {}
    NameBaseNumberMap(const NameBaseNumberMap &) = delete;
    NameBaseNumberMap &operator=(const NameBaseNumberMap &) = delete;

    int getCounterBaseNumber(const std::string &counterName);

private:
    // Fill name -> counter ID maps lazily when first needed.
    std::vector<std::unordered_map<std::string, DWORD>> _nameIdMaps;

    Logger *_logger;
    const WinApiInterface &_winapi;
};

class SectionPerfcounter : public Section {
public:
    SectionPerfcounter(const std::string &outputName,
                       const std::string &configName, const Environment &env,
                       NameBaseNumberMap &nameNumberMap, Logger *logger,
                       const WinApiInterface &winapi);

protected:
    virtual bool produceOutputInner(
        std::ostream &out, const std::optional<std::string> &) override;

private:
    time_t _disabled_until{0};
    NameBaseNumberMap &_nameNumberMap;
};

#endif  // SectionPerfcounter_h
