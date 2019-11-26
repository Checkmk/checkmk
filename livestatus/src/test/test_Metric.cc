#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <string>
#include <vector>
#include "Logger.h"
#include "Metric.h"
#include "gtest/gtest.h"

namespace fs = std::filesystem;

namespace {
void touch(fs::path&& p) { std::ofstream{p}; };
}  // namespace

bool operator<(const Metric::MangledName& x, const Metric::MangledName& y) {
    return x.string() < y.string();
}

class MetricFixture : public ::testing::Test {
public:
    const std::string desc = "Service_Description";
    const std::string other_d = "Other_Service_Description";
    Metric::Names metrics = {Metric::MangledName{"abc"},
                             Metric::MangledName{"def"},
                             Metric::MangledName{"ghi"}};
    Metric::Names other_m = {Metric::MangledName{"jkl"},
                             Metric::MangledName{"mno"},
                             Metric::MangledName{"pqr"}};
    const std::string ext = ".rrd";
    const fs::path basepath{fs::temp_directory_path() / "metric_tests"};
    fs::path filename(const std::string& d, const Metric::MangledName& metric) {
        return basepath / (d + "_" + metric.string() + ext);
    }

    void SetUp() override {
        std::sort(metrics.begin(), metrics.end());
        fs::create_directories(basepath);
        // Create the metrics we use for the test.
        std::for_each(std::begin(metrics), std::end(metrics),
                      [&](auto&& m) { touch(filename(desc, m)); });
        // Add non-matching metrics to the directory.
        std::for_each(
            std::begin(other_m), std::end(other_m),
            [&](const auto& m) { std::ofstream(filename(other_d, m)); });
    }
    void TearDown() override { fs::remove_all(basepath); }
};

TEST_F(MetricFixture, DirectoryAndFileExist) {
    ASSERT_TRUE(fs::exists(basepath));
    EXPECT_FALSE(fs::is_empty(basepath));
    for (auto&& m : metrics) {
        EXPECT_TRUE(fs::exists(filename(desc, m)));
    }
    for (auto&& m : other_m) {
        EXPECT_TRUE(fs::exists(filename(other_d, m)));
    }
}

TEST_F(MetricFixture, ScanRRDFindsMetrics) {
    ASSERT_TRUE(fs::exists(basepath));
    Logger* const logger{Logger::getLogger("test")};
    Metric::Names names;
    scan_rrd(basepath, desc, names, logger);
    std::sort(names.begin(), names.end());
    ASSERT_EQ(metrics, names);
}
