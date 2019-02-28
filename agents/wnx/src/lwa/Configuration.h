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

#include <filesystem>
#include <map>
#include <memory>

#include "SettingsCollector.h"

class ConfigurableBase;

using ConfigKey = std::pair<std::string, std::string>;
#if defined(USE_UNIQUE_PTR_WITHOUT_UNDERSTANDING_WHAT_UNIQUE_MEANS)
using ConfigurableVector = std::vector<std::unique_ptr<ConfigurableBase>>;
#else
using ConfigurableVector = std::vector<ConfigurableBase *>;
#endif
using ConfigurableMap = std::map<ConfigKey, ConfigurableVector>;

bool readConfigFile(std::istream &is, const std::string &hostname,
                    ConfigurableMap &configurables);

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
    explicit Configuration() {}
    Configuration(Configuration &) = delete;
    Configuration &operator=(const Configuration &) = delete;

    void outputConfigurables(std::ostream &out);

    void outputConfigurables(
        std::function<void(std::string, std::string, std::string, std::string)>
            Sink);

    bool ReadSettings(std::filesystem::path Path, bool Local) noexcept;

    void reg(const char *section, const char *key, ConfigurableBase *cfg);

    const auto size() const { return _configurables.size(); }

private:
    ConfigurableMap _configurables;
};

#endif  // Configuration_h
