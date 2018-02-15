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
    explicit ParseError(const std::string &what, unsigned lineno)
        : std::runtime_error(what), _lineno(lineno) {}

    unsigned getLineNo() const { return _lineno; }

private:
    unsigned _lineno{0};
};

using ConfigKey = std::pair<std::string, std::string>;
using ConfigurableMap =
    std::map<ConfigKey, std::vector<std::unique_ptr<ConfigurableBase>>>;

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
