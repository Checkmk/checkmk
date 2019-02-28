
// provides basic api to start and stop service

#pragma once
#ifndef p_perf_counters_h__
#define p_perf_counters_h__

#include <chrono>
#include <condition_variable>
#include <mutex>
#include <string>

#include "carrier.h"

#include "section_header.h"

#include "providers/internal.h"

namespace cma {

namespace provider {
class UptimeSync : public Synchronous {
public:
    UptimeSync() : Synchronous(cma::section::kUptimeName, 0) {}

    UptimeSync(const std::string& Name, char Separator = 0)
        : Synchronous(Name, Separator) {}

protected:
    virtual std::string makeBody() const override;
};

class Uptime : public Asynchronous {
public:
    Uptime() : Asynchronous(cma::section::kUptimeName, 0) {}

    Uptime(const std::string& Name, char Separator = 0)
        : Asynchronous(Name, Separator) {}

protected:
    virtual std::string makeBody() const override;
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
std::string MakeWinPerfHeader(const std::wstring& Prefix,
                              const std::wstring& Name);
std::string MakeWinPerfNakedList(const PERF_OBJECT_TYPE* Object,
                                 uint32_t KeyIndex);
}  // namespace details

std::string BuildWinPerfSection(const std::wstring& Prefix,
                                const std::wstring& Name,
                                const std::wstring& Key);

}  // namespace provider

};  // namespace cma

#endif  // p_perf_counters_h__
