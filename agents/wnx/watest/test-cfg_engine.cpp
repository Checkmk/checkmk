// test-yaml.cpp :
// YAML and around

#include "pch.h"

#include "wnx/cfg_engine.h"

// we want to avoid those data public
namespace cma::cfg::engine {
TEST(CfgEngine, All) {
    EXPECT_EQ(logwatch::kMaxSize, 500000);
    EXPECT_EQ(logwatch::kMaxEntries, -1);
    EXPECT_EQ(logwatch::kMaxLineLength, -1);
    EXPECT_EQ(logwatch::kTimeout, -1);
}

}  // namespace cma::cfg::engine
