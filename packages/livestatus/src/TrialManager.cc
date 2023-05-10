// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// IWYU pragma: no_include <type_traits>
#include "livestatus/TrialManager.h"

#include <endian.h>

#include <cstdint>
#include <istream>
#include <stdexcept>
#include <system_error>

#include "livestatus/Logger.h"

void TrialManager::validateServiceCount(
    std::chrono::system_clock::time_point now, size_t num_services) const {
    if (is_licensed_ || !isTrialExpired(now)) {
        return;
    }

    if (num_services > maxServicesInTrialPeriod()) {
        auto days = mk::ticks<mk::days>(trialPeriod());
        throw std::runtime_error(
            "The " + std::to_string(days) +
            "-day trial is over and you are exceeding the limits of your Checkmk installation. Only max. " +
            std::to_string(maxServicesInTrialPeriod()) +
            " services with max. 1 site are possible, not " +
            std::to_string(num_services) +
            " services. Please apply a valid license or adjust your configuration to be able to monitor again. Exiting...");
    }
}

bool TrialManager::isTrialExpired(
    std::chrono::system_clock::time_point now) const {
    return now > state_file_created_ + trialPeriod();
}

std::string TrialManager::state(
    std::chrono::system_clock::time_point now) const {
    return is_licensed_          ? "licensed"
           : isTrialExpired(now) ? "expired trial"
                                 : "active trial";
}

namespace {
uint64_t readle64(std::istream &is) {
    // TODO(sp): Use std::endian + std::byteswap when we have C++23
    uint64_t buffer{};
    is.read(reinterpret_cast<char *>(&buffer), sizeof(buffer));
    return le64toh(buffer);
}

void writele64(std::ostream &os, uint64_t value) {
    // TODO(sp): Use std::endian + std::byteswap when we have C++23
    uint64_t buffer{htole64(value)};
    os.write(reinterpret_cast<const char *>(&buffer), sizeof(buffer));
}
}  // namespace

namespace mk {
std::chrono::system_clock::time_point state_file_created(
    const std::filesystem::path &state_file_created_file,
    std::chrono::system_clock::time_point default_creation_time) {
    std::ifstream ifs{state_file_created_file, std::ios::binary};
    if (ifs.is_open()) {
        return mk::demangleTimePoint(readle64(ifs));
    }
    if (generic_error{}.code() != std::errc::no_such_file_or_directory) {
        throw generic_error{"cannot open timestamp file \"" +
                            state_file_created_file.string() +
                            "\" for reading"};
    }
    auto state_file_created_dir = state_file_created_file.parent_path();
    std::filesystem::create_directories(state_file_created_dir);
    std::ofstream ofs{state_file_created_file, std::ios::binary};
    if (!ofs.is_open()) {
        throw generic_error{"cannot open timestamp file \"" +
                            state_file_created_file.string() +
                            "\" for writing"};
    }
    writele64(ofs, mk::mangleTimePoint(default_creation_time));
    return default_creation_time;
}

bool is_licensed(const std::filesystem::path &licensed_state_file) {
    char state{'0'};
    if (std::ifstream ifs{licensed_state_file, std::ios::binary}) {
        ifs.read(&state, sizeof(state));
    };
    return state == '1';
}

TrialManager validate_license(
    std::chrono::system_clock::time_point state_file_created, bool is_licensed,
    std::chrono::system_clock::time_point now, size_t num_services) {
    TrialManager trial_manager{state_file_created, is_licensed};
    trial_manager.validateServiceCount(now, num_services);
    return trial_manager;
}
}  // namespace mk
