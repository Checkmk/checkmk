
// provides basic api to start and stop service

#pragma once
#ifndef p_perf_counters_h__
#define p_perf_counters_h__

#include <string>
#include <string_view>

#include "providers/internal.h"
#include "section_header.h"

namespace cma {

namespace provider {
class UptimeSync : public Synchronous {
public:
    UptimeSync() : Synchronous(cma::section::kUptimeName, 0) {}

    UptimeSync(const std::string& Name, char Separator = 0)
        : Synchronous(Name, Separator) {}

protected:
    std::string makeBody() override;
};

class UptimeAsync : public Asynchronous {
public:
    UptimeAsync() : Asynchronous(cma::section::kUptimeName, 0) {}

    UptimeAsync(const std::string& Name, char Separator = 0)
        : Asynchronous(Name, Separator) {}

protected:
    std::string makeBody() override;
};

// too simple for class object!
// probably should go in another namespace(used also by skype)
namespace details {
// low level registry scanners

wtools::perf::DataSequence LoadWinPerfData(const std::wstring& Key,
                                           uint32_t& KeyIndex);

// low level printers
// first line
std::string MakeWinPerfStamp(uint32_t KeyIndex);
// header
std::string MakeWinPerfHeader(std::wstring_view prefix, std::wstring_view name);
std::string MakeWinPerfNakedList(const PERF_OBJECT_TYPE* Object,
                                 uint32_t KeyIndex);
}  // namespace details

std::string BuildWinPerfSection(std::wstring_view prefix,
                                std::wstring_view name, std::wstring_view key);

}  // namespace provider

};  // namespace cma

#endif  // p_perf_counters_h__
