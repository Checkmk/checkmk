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
#include "SettingsCollector.h"
#undef CreateMutex
#include "types.h"

class ConfigurableBase;
class Environment;

/* Example configuration file:

   [global]
# Process this logfile only on the following hosts
only_on = zhamzr12

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
    typedef std::pair<std::string, std::string> ConfigKey;

    ConfigKey config_key(const std::string &section, const std::string &key) {
        return std::make_pair(section, key);
    }

public:
    Configuration(const Environment &env);
    ~Configuration();

    void outputConfigurables(std::ostream &out);
    void readSettings();

    void reg(const char *section, const char *key, ConfigurableBase *cfg);
    void deregister(const char *section, const char *key,
                    ConfigurableBase *cfg);
    inline const Environment &getEnvironment() const { return _environment; }

    static std::string configFileName(bool local, const Environment &env);

private:
    void readConfigFile(const std::string &filename);

    bool checkHostRestriction(char *patterns);

private:
    typedef std::pair<std::string, std::string> ConfigurableKey;
    std::map<ConfigurableKey, std::vector<ConfigurableBase *>> _configurables;

    const Environment &_environment;
};

#endif  // Configuration_h
