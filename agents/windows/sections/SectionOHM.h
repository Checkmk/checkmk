// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#ifndef SectionOHM_h
#define SectionOHM_h

#include "Configurable.h"
#include "OHMMonitor.h"
#include "SectionWMI.h"

class Configuration;

class SectionOHM : public SectionWMI {
public:
    SectionOHM(Configuration &config, Logger *logger,
               const WinApiInterface &winapi);

    virtual void startIfAsync();

protected:
    virtual bool produceOutputInner(
        std::ostream &out, const std::optional<std::string> &remoteIP) override;

private:
    OHMMonitor _ohm_monitor;
};

#endif  // SectionOHM_h
