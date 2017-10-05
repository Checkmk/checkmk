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

#ifndef Section_h
#define Section_h

#include <chrono>
#include <future>
#include <iostream>
#include <map>
#include <memory>
#include <string>
#include <vector>
#include "WinApiAdaptor.h"

class Environment;
class Logger;
class WinApiAdaptor;

class Section {
    friend class SectionGroup;

    const std::string _outputName;
    const std::string _configName;
    bool _show_header{true};
    char _separator{' '};
    bool _realtime_support{false};

protected:
    const Environment &_env;
    Logger *_logger;
    const WinApiAdaptor &_winapi;

public:
    Section(const std::string &outputName, const std::string &configName,
            const Environment &env, Logger *logger,
            const WinApiAdaptor &winapi);

    virtual ~Section() = default;

    Section *withSeparator(char sep) {
        _separator = sep;
        return this;
    }

    Section *withHiddenHeader(bool hidden = true);
    Section *withRealtimeSupport();

    std::string outputName() const { return _outputName; }
    std::string configName() const { return _configName; }

    virtual void postprocessConfig() {}

    /// TODO please implement me
    virtual void startIfAsync() {}
    virtual void waitForCompletion() {}
    /**
     * signal termination to all threads and return all thread handles
     * used by the section. The caller will give the threads a chance
     * to complete
     **/
    virtual std::vector<HANDLE> stopAsync() { return std::vector<HANDLE>(); }

    bool produceOutput(std::ostream &out, bool nested = false);

    virtual bool isEnabled() const { return true; }
    virtual bool realtimeSupport() const { return _realtime_support; }

protected:
    char separator() const { return _separator; }

private:
    bool generateOutput(std::string &buffer);
    virtual bool produceOutputInner(std::ostream &out) = 0;
};

#endif  // Section_h
