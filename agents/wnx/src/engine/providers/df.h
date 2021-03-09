
// provides basic api to start and stop service

#pragma once
#ifndef df_h__
#define df_h__

#include <string>

#include "providers/internal.h"
#include "section_header.h"

namespace cma {

namespace provider {

constexpr char kDfSeparator = section::kTabSeparator;
constexpr auto kDfSeparatorString = section::kTabSeparatorString;

class Df : public Asynchronous {
public:
    Df() : Asynchronous(cma::section::kDfName, '\t') {}

    Df(const std::string& Name, char Separator)
        : Asynchronous(Name, Separator) {}

private:
    std::string makeBody() override;
};

// internal df functionality
namespace df {
std::pair<std::string, std::string> GetNamesByVolumeId(
    std::string_view volume_id);
std::pair<uint64_t, uint64_t> GetSpacesByVolumeId(std::string_view volume_id);
std::string ProduceFileSystemOutput(std::string_view volume_id);
std::vector<std::string> GetMountPointVector(std::string_view volume_id);
std::string ProduceMountPointsOutput(const std::string& VolumeId);
std::vector<std::string> GetDriveVector() noexcept;
uint64_t CalcUsage(uint64_t avail, uint64_t total);
}  // namespace df

}  // namespace provider

};  // namespace cma

#endif  // df_h__
