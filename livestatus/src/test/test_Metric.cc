// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <string>
#include <vector>

#include "Logger.h"
#include "Metric.h"
#include "gtest/gtest.h"
#include "pnp4nagios.h"

namespace fs = std::filesystem;

bool operator<(const Metric::MangledName &x, const Metric::MangledName &y) {
    return x.string() < y.string();
}

class MetricFixture : public ::testing::Test {
public:
    const std::string ext = ".xml";
    const std::string desc = "Service Description";
    const Metric::Names metrics = {Metric::MangledName{"abc 1"},
                                   Metric::MangledName{"def 2"},
                                   Metric::MangledName{"ghi 3"}};
    const std::string desc_other = "Service Description Other";
    const Metric::Names metrics_other = {Metric::MangledName{"jkl 4"},
                                         Metric::MangledName{"mno 5"},
                                         Metric::MangledName{"pqr 6"}};
    const fs::path basepath{fs::temp_directory_path() / "metric_tests"};

    static void dump(fs::path &&path, const Metric::Names &metrics) {
        auto out = std::ofstream{path};
        out << "<?xml version=\"1.0\">\n"
               "<NAGIOS>\n";
        for (auto &&m : metrics) {
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
        fs::create_directories(basepath);
        // Create the metrics we use for the test.
        dump(basepath / pnp_cleanup(desc + ext), metrics);
        // Add non-matching metrics to the directory.
        dump(basepath / pnp_cleanup(desc_other + ext), metrics_other);
    }
    void TearDown() override { fs::remove_all(basepath); }
};

/// Return sorted string vectors to make the diff readable.
std::vector<std::string> human_readable(const Metric::Names &in) {
    std::vector<std::string> out(in.size());
    std::transform(std::begin(in), std::end(in), std::begin(out),
                   [](auto &&elem) { return elem.string(); });
    std::sort(std::begin(out), std::end(out));
    return out;
}

TEST_F(MetricFixture, ScanRRDFindsMetrics) {
    ASSERT_TRUE(fs::exists(basepath));
    ASSERT_FALSE(fs::is_empty(basepath));
    Logger *const logger{Logger::getLogger("test")};

    const auto names = scan_rrd(basepath, desc, logger);
    EXPECT_EQ(human_readable(metrics), human_readable(names));
}
