// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#ifndef Section_h
#define Section_h

#include <chrono>
#include <future>
#include <iostream>
#include <map>
#include <memory>
#include <optional>
#include <string>
#include <vector>

#include "WinApiInterface.h"

class Environment;
class Logger;
class SectionHeaderBase;

namespace section_helpers {

template <class ToDuration = std::chrono::seconds, class Rep = long long>
inline Rep current_time() {
    const std::chrono::duration<Rep> now =
        std::chrono::duration_cast<ToDuration>(
            std::chrono::system_clock::now().time_since_epoch());
    return now.count();
}

}  // namespace section_helpers

class Section {
public:
    Section(const std::string &configName, const Environment &env,
            Logger *logger, const WinApiInterface &winapi,
            std::unique_ptr<SectionHeaderBase> header);

    virtual ~Section();

    virtual void postprocessConfig() {}

    /// TODO please implement me
    virtual void startIfAsync() {}
    virtual void waitForCompletion() {}
    /**
     * signal termination to all threads and return all thread handles
     * used by the section. The caller will give the threads a chance
     * to complete
     **/
    virtual std::vector<HANDLE> stopAsync() { return {}; }

    bool produceOutput(std::ostream &out,
                       const std::optional<std::string> &remoteIP);
    std::string configName() const { return _configName; }

protected:
    const std::string _configName;
    const Environment &_env;
    Logger *_logger;
    const WinApiInterface &_winapi;

private:
    virtual bool produceOutputInner(
        std::ostream &out, const std::optional<std::string> &remoteIP) = 0;
    bool generateOutput(std::string &buffer,
                        const std::optional<std::string> &remoteIP);

protected:
    std::unique_ptr<SectionHeaderBase> _header;
};

constexpr const char kTabSeparator = '\t';
constexpr const char kPipeSeparator = '|';
constexpr const wchar_t *kWidePipeSeparator = L"|";
constexpr const wchar_t *kWideTabSeparator = L"\t";

#endif  // Section_h
