#include "pch.h"

#include <string>
#include <vector>

#include "cfg.h"
#include "common/wtools.h"
#include "providers/perf_cpuload.h"
#include "service_processor.h"
#include "test_tools.h"

namespace cma::provider {

class PerfCpuLoadTest : public ::testing::Test {
public:
    srv::SectionProvider<PerfCpuLoad> cpuload_provider;
    PerfCpuLoad &getEngine() { return cpuload_provider.getEngine(); }
    std::vector<std::string> getOutput() {
        return tools::SplitString(getEngine().generateContent(), "\n");
    }

    inline static const std::vector<std::pair<int, std::string>> checks{
        {0, section::MakeHeader(kWmiCpuLoad, PerfCpuLoad::kSepChar)},
        {1, section::MakeSubSectionHeader(kSubSectionSystemPerf)},
        {2,
         fmt::format(
             "Name{0}ProcessorQueueLength{0}Timestamp_PerfTime{0}Frequency_PerfTime{0}WMIStatus\n",
             PerfCpuLoad::kSepChar)},
        {4, section::MakeSubSectionHeader(kSubSectionComputerSystem)},
        {5,
         fmt::format(
             "Name{0}NumberOfLogicalProcessors{0}NumberOfProcessors{0}WMIStatus\n",
             PerfCpuLoad::kSepChar)}

    };
};

TEST_F(PerfCpuLoadTest, Construction) {
    EXPECT_EQ(getEngine().getUniqName(), kWmiCpuLoad);
    EXPECT_EQ(getEngine().separator(), PerfCpuLoad::kSepChar);
}

TEST_F(PerfCpuLoadTest, Generation) {
    uint64_t low = wtools::QueryPerformanceCo();
    auto table = getOutput();
    uint64_t high = wtools::QueryPerformanceCo();

    ASSERT_EQ(table.size(), 7);

    for (const auto &[i, val] : checks) {
        EXPECT_EQ(table[i] + "\n", val) << fmt::format("at index {}", i);
    }

    auto perfs =
        tools::SplitString(table[3], fmt::format("{}", PerfCpuLoad::kSepChar));
    ASSERT_EQ(perfs.size(), 5);

    EXPECT_TRUE(perfs[0].empty());

    auto queue_length = std::stoull(perfs[1]);
    EXPECT_LT(queue_length, 10000u);
    auto perf_time = std::stoull(perfs[2]);
    EXPECT_TRUE(low <= perf_time && perf_time <= high);
    EXPECT_GT(std::stoull(perfs[3]), 0u);
    EXPECT_EQ(perfs[4], "OK");

    auto cpus =
        tools::SplitString(table[6], fmt::format("{}", PerfCpuLoad::kSepChar));
    ASSERT_EQ(cpus.size(), 4);
    ASSERT_FALSE(cpus[1].empty() && cpus[2].empty())
        << "bad line is:" << table[6];
    EXPECT_FALSE(cpus[0].empty());
    auto cpu_count = std::stoull(cpus[1]);
    EXPECT_TRUE(1 <= cpu_count && cpu_count <= 16u);
    auto cpu_count_phys = std::stoull(cpus[2]);
    EXPECT_GT(cpu_count_phys, 0u);
    EXPECT_EQ(cpus[3], "OK");
}

}  // namespace cma::provider
