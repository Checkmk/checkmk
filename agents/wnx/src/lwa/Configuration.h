// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef Configuration_h
#define Configuration_h

#include <filesystem>
#include <functional>
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

    bool ReadSettings(const std::filesystem::path &Path, bool Local) noexcept;

    void reg(const char *section, const char *key, ConfigurableBase *cfg);

    const auto size() const { return _configurables.size(); }

private:
    ConfigurableMap _configurables;
};

#endif  // Configuration_h
