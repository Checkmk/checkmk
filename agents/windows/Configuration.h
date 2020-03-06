// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#ifndef Configuration_h
#define Configuration_h

#include <map>
#include <memory>
#include "Environment.h"
#include "SettingsCollector.h"

class ConfigurableBase;
class Environment;

class ParseError : public std::runtime_error {
public:
    explicit ParseError(const std::string &what) : std::runtime_error(what) {}
};

using ConfigKey = std::pair<std::string, std::string>;
using ConfigurableVector = std::vector<std::unique_ptr<ConfigurableBase>>;
using ConfigurableMap = std::map<ConfigKey, ConfigurableVector>;

void readConfigFile(std::istream &is, const std::string &hostname,
                    ConfigurableMap &configurables);

inline std::string configFileName(bool local, const Environment &env) {
    return env.agentDirectory() + "\\" + "check_mk" + (local ? "_local" : "") +
           ".ini";
}

/* Example configuration file:

   [global]
# Process this logfile only on the following hosts
host = zhamzr12

# Restrict access to certain IP addresses
only_from = 127.0.0.1 192.168.56.0/24

# Enable crash debugging
crash_debug = on


[winperf]
# Select counters to extract. The following counters
# are needed by checks shipped with check_mk.
counters = 10332:msx_queues

[logwatch]
# Select which messages are to be sent in which
# event log
logfile system      = off
logfile application = info
logfile *           = off

[mrpe]
check = DISK_C: mrpe/check_disk -w C:
check = MEM mrpe/check_mem -w 10 -c 20
 */
class Configuration {
public:
    explicit Configuration(const Environment &env) : _environment(env) {}
    Configuration(Configuration &) = delete;
    Configuration &operator=(const Configuration &) = delete;

    void outputConfigurables(std::ostream &out);
    void readSettings();

    void reg(const char *section, const char *key, ConfigurableBase *cfg);
    inline const Environment &getEnvironment() const { return _environment; }

private:
    ConfigurableMap _configurables;
    const Environment &_environment;
};

#endif  // Configuration_h
