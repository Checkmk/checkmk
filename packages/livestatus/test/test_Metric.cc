// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <string>
#include <vector>

#include "gtest/gtest.h"
#include "livestatus/Logger.h"
#include "livestatus/Metric.h"
#include "livestatus/PnpUtils.h"

namespace {
// NOLINTBEGIN(cert-err58-cpp)
const std::filesystem::path basepath{std::filesystem::temp_directory_path() /
                                     "metric_tests"};
const std::string ext = ".xml";

const std::string desc = "Service Description";
const Metric::Names metrics = {Metric::MangledName{"abc 1"},
                               Metric::MangledName{"def 2"},
                               Metric::MangledName{"ghi 3"}};

const std::string desc_other = "Service Description Other";
const Metric::Names metrics_other = {Metric::MangledName{"jkl 4"},
                                     Metric::MangledName{"mno 5"},
                                     Metric::MangledName{"pqr 6"}};
// NOLINTEND(cert-err58-cpp)
}  // namespace

class MetricFixture : public ::testing::Test {
public:
    static void dump(const std::filesystem::path &path,
                     const Metric::Names &metrics) {
        auto out = std::ofstream{path};
        out << "<?xml version=\"1.0\">\n"
               "<NAGIOS>\n";
        for (const auto &m : metrics) {
            out << "  <DATASOURCE>\n";
            out << "    <TEMPLATE>template</TEMPLATE>\n";
            out << "    <NAME>" + m.string() + "</NAME>\n";
            out << "    <LABEL>" + m.string() + "</LABEL>\n";
            out << "    <UNIT></UNIT>\n";
            out << "  </DATASOURCE>\n";
        }
        out << "  <XML>\n"
               "    <VERSION>4</VERSION>"
               "\n  </XML>\n"
               "</NAGIOS>\n";
    }

    void SetUp() override {
        std::filesystem::create_directories(basepath);
        // Create the metrics we use for the test.
        dump(basepath / pnp_cleanup(desc + ext), metrics);
        // Add non-matching metrics to the directory.
        dump(basepath / pnp_cleanup(desc_other + ext), metrics_other);
    }
    void TearDown() override { std::filesystem::remove_all(basepath); }
};

TEST_F(MetricFixture, ScanRRDFindsMetrics) {
    /// Return sorted string vectors to make the diff readable.
    auto human_readable = [](const Metric::Names &in) {
        std::vector<std::string> out(in.size());
        std::ranges::transform(in, std::begin(out),
                               [](auto &&elem) { return elem.string(); });
        std::ranges::sort(out);
        return out;
    };

    ASSERT_TRUE(std::filesystem::exists(basepath));
    ASSERT_FALSE(std::filesystem::is_empty(basepath));
    Logger *const logger{Logger::getLogger("test")};

    const auto names = scan_rrd(basepath, desc, logger);
    EXPECT_EQ(human_readable(metrics), human_readable(names));
}
