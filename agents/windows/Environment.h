// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#ifndef Environment_h
#define Environment_h

#include <string>
#include "types.h"

class Logger;
class WinApiInterface;

class Environment {
public:
    Environment(bool use_cwd, bool with_stderr, Logger *logger,
                const WinApiInterface &winapi);
    virtual ~Environment();

    // TODO: this is an evil hack, but currently there is at least one global
    // function that requires access to the env that isn't easily refactored
    static Environment *instance();

    virtual std::string hostname() const { return _hostname; }

    virtual std::string currentDirectory() const { return _current_directory; }
    virtual std::string agentDirectory() const { return _agent_directory; }

    virtual std::string pluginsDirectory() const { return _plugins_directory; }
    virtual std::string configDirectory() const { return _config_directory; }
    virtual std::string localDirectory() const { return _local_directory; }
    virtual std::string spoolDirectory() const { return _spool_directory; }
    virtual std::string stateDirectory() const { return _state_directory; }
    virtual std::string tempDirectory() const { return _temp_directory; }
    virtual std::string logDirectory() const { return _log_directory; }
    virtual std::string binDirectory() const { return _bin_directory; }

    virtual std::string logwatchStatefile() const {
        return _logwatch_statefile;
    }
    virtual std::string eventlogStatefile() const {
        return _eventlog_statefile;
    }

    virtual const JobHandle<0> &workersJobObject() const {
        return _workers_job_object;
    }

    virtual bool withStderr() const { return _with_stderr; }

    virtual bool isWinNt() const;

    // return windows version as a combined value, with major version in the
    // upper 8 bits
    // and minor in the lower bits, i.e. 0x0501 for windows xp (32-bit)
    virtual uint16_t winVersion() const;

private:
    std::string determineHostname() const;
    std::string determineCurrentDirectory() const;
    std::string determineAgentDirectory(bool use_cwd) const;
    std::string assignDirectory(const char *name) const;

    static Environment *s_Instance;

    Logger *_logger;
    const WinApiInterface &_winapi;

    const std::string _hostname;

    const std::string _current_directory;
    const std::string _agent_directory;
    const std::string _plugins_directory;
    const std::string _config_directory;
    const std::string _local_directory;
    const std::string _spool_directory;
    const std::string _state_directory;
    const std::string _temp_directory;
    const std::string _log_directory;
    const std::string _bin_directory;

    const std::string _logwatch_statefile;
    const std::string _eventlog_statefile;

    // Job object for all worker threads
    // Gets terminated on shutdown
    JobHandle<0> _workers_job_object;
    const bool _with_stderr{false};
};

// in main
namespace cma {
std::string GetServiceDirectory();  // from the registry
std::wstring GetAgentParentPath();  // from starting module
};                                  // namespace cma

#endif  // Environment_h
