
// provides basic api to start and stop service

#pragma once
#ifndef ohm_h__
#define ohm_h__

#include <filesystem>
#include <string>
#include <string_view>

#include "cma_core.h"
#include "section_header.h"

#include "providers/internal.h"
#include "providers/wmi.h"

namespace cma::provider {
std::filesystem::path GetOhmCliPath();

constexpr std::string_view kOpenHardwareMonitorCli =
    "OpenHardwareMonitorCLI.exe";

// openhardwaremonitor:
class OhmProvider : public Wmi {
public:
    OhmProvider(const std::string& Name, char Separator)
        : Wmi(Name, Separator) {}

    virtual void loadConfig();

    virtual void updateSectionStatus();

protected:
    // virtual std::string makeBody() const override;

#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class OhmTest;
    FRIEND_TEST(OhmTest, Base);
#endif
};

}  // namespace cma::provider

#endif  // ohm_h__
