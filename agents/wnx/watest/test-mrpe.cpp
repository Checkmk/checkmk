// watest.cpp : This file contains the 'main' function. Program execution begins
// and ends there.
//
#include "pch.h"

#include <string>  // for string

#include "cfg.h"
#include "on_start.h"  // for OnStart, AppType, AppType::test
#include "providers/mrpe.h"
#include "system_error"  // for error_code
#include "test_tools.h"

std::string_view a;
/*
Typic output:

<<<mrpe>>>
(mode.com) Console 0 Status von Gert CON: 1 --------------------- 1
Codepage:        437 (chcp.com) sk 1 Geben Sie das Kennwort fuer "sk" ein:
*/

namespace cma::provider {  // to become friendly for wtools classes

class YamlLoaderMrpe {
public:
    YamlLoaderMrpe() {
        using namespace cma::cfg;
        std::error_code ec;
        std::filesystem::remove(cma::cfg::GetBakeryFile(), ec);
        cma::OnStart(cma::AppType::test);

        auto yaml = GetLoadedConfig();
        auto sections =
            GetInternalArray(groups::kGlobal, vars::kSectionsEnabled);
        sections.push_back(groups::kMrpe);
        PutInternalArray(groups::kGlobal, vars::kSectionsEnabled, sections);
        yaml[groups::kGlobal].remove(vars::kSectionsDisabled);
        yaml[groups::kGlobal][vars::kLogDebug] = "all";
        ProcessKnownConfigGroups();
        SetupEnvironmentFromGroups();
    }
    ~YamlLoaderMrpe() { OnStart(cma::AppType::test); }
};

TEST(SectionProviderMrpe, Construction) {
    YamlLoaderMrpe w;
    using namespace cma::cfg;
    EXPECT_TRUE(cma::cfg::groups::global.allowedSection(groups::kMrpe));
    MrpeProvider mrpe;
    EXPECT_EQ(mrpe.getUniqName(), cma::section::kMrpe);
    EXPECT_EQ(mrpe.accu_.size(), 0);
    EXPECT_EQ(mrpe.checks_.size(), 0);
    EXPECT_EQ(mrpe.entries_.size(), 0);
    EXPECT_EQ(mrpe.includes_.size(), 0);
    auto out = mrpe.makeBody();
    EXPECT_TRUE(out.empty());
    mrpe.accu_.push_back('a');
    mrpe.accu_.push_back('\n');
    out = mrpe.generateContent(cma::section::kUseEmbeddedName);
    // very simple : concatenate accu_ and makeHeader
    EXPECT_EQ(out, "<<<mrpe>>>\na\n") << out;
}

void replaceYamlSeq(const std::string Group, const std::string SeqName,
                    std::vector<std::string> Vec) {
    YAML::Node Yaml = cma::cfg::GetLoadedConfig();
    for (size_t i = 0; i < Yaml[Group][SeqName].size(); i++)
        Yaml[Group][SeqName].remove(0);

    Yaml[Group][SeqName].reset();

    for (auto& str : Vec) {
        Yaml[Group][SeqName].push_back(str);
    }
}

TEST(SectionProviderMrpe, SmallApi) {
    YamlLoaderMrpe w;
    std::string s = "a\rb\n\n";
    FixCrCnForMrpe(s);
    EXPECT_EQ(s, "a b\1\1");

    {
        auto [user, path] = cma::provider::parseIncludeEntry(
            "sk = $CUSTOM_AGENT_PATH$\\mrpe_checks.cfg");
        EXPECT_EQ(user, "sk");
        EXPECT_EQ(path.u8string(),
                  wtools::ConvertToUTF8(cma::cfg::GetUserDir()) + "\\" +
                      "mrpe_checks.cfg");
    }
}

TEST(SectionProviderMrpe, ConfigLoad) {
    ASSERT_TRUE(true);
    YamlLoaderMrpe w;
    using namespace cma::cfg;
    MrpeProvider mrpe;
    EXPECT_EQ(mrpe.getUniqName(), cma::section::kMrpe);
    auto yaml = GetLoadedConfig();
    ASSERT_TRUE(yaml.IsMap());

    auto mrpe_yaml_optional = GetGroup(yaml, groups::kMrpe);
    ASSERT_TRUE(mrpe_yaml_optional.has_value());
    {
        auto& mrpe_cfg = mrpe_yaml_optional.value();

        ASSERT_TRUE(GetVal(mrpe_cfg, vars::kEnabled, false));
        auto entries = GetArray<std::string>(mrpe_cfg, vars::kMrpeConfig);
        EXPECT_EQ(entries.size(), 0)
            << "no mrpe expected";  // include and check
    }

    replaceYamlSeq(
        groups::kMrpe, vars::kMrpeConfig,
        {"check = Console 'c:\\windows\\system32\\mode.com' CON CP /STATUS",
         "include sk = $CUSTOM_AGENT_PATH$\\mrpe_checks.cfg",  // reference
         "Include=$CUSTOM_AGENT_PATH$\\mrpe_checks.cfg",  // valid without space
         "include  =   'mrpe_checks.cfg'",                //
         "includes = $CUSTOM_AGENT_PATH$\\mrpe_checks.cfg",  // invalid
         "includ = $CUSTOM_AGENT_PATH$\\mrpe_checks.cfg",    // invalid
         "chck = Console 'c:\\windows\\system32\\mode.com' CON CP /STATUS",  // invalid
         "check = 'c:\\windows\\system32\\mode.com' CON CP /STATUS"});  // valid

    auto strings = GetArray<std::string>(groups::kMrpe, vars::kMrpeConfig);
    EXPECT_EQ(strings.size(), 8);
    mrpe.parseConfig();
    ASSERT_EQ(mrpe.includes_.size(), 3);
    mrpe.parseConfig();
    ASSERT_EQ(mrpe.includes_.size(), 3);
    EXPECT_EQ(mrpe.includes_[0], "sk = $CUSTOM_AGENT_PATH$\\mrpe_checks.cfg");
    EXPECT_EQ(mrpe.includes_[1], "=$CUSTOM_AGENT_PATH$\\mrpe_checks.cfg");
    EXPECT_EQ(mrpe.includes_[2], "=   'mrpe_checks.cfg'");
    ASSERT_EQ(mrpe.checks_.size(), 2);
    EXPECT_EQ(mrpe.checks_[0],
              "Console 'c:\\windows\\system32\\mode.com' CON CP /STATUS");
    EXPECT_EQ(mrpe.checks_[1],
              "'c:\\windows\\system32\\mode.com' CON CP /STATUS");

    mrpe.addParsedConfig();
    EXPECT_EQ(mrpe.includes_.size(), 3);
    EXPECT_EQ(mrpe.checks_.size(), 2);
    EXPECT_EQ(mrpe.entries_.size(), 4);
}

TEST(SectionProviderMrpe, YmlCheck) {
    using namespace cma::cfg;
    tst::YamlLoader w;
    auto cfg = cma::cfg::GetLoadedConfig();

    auto mrpe_node = cfg[groups::kMrpe];
    ASSERT_TRUE(mrpe_node.IsDefined());
    ASSERT_TRUE(mrpe_node.IsMap());

    auto enabled = GetVal(groups::kMrpe, vars::kEnabled, false);
    EXPECT_TRUE(enabled);
    auto paths = GetArray<std::string>(groups::kMrpe, vars::kMrpeConfig);
    EXPECT_EQ(paths.size(), 0) << "base YAML must have 0 mrpe entries";
}

TEST(SectionProviderMrpe, Run) {
    YamlLoaderMrpe w;
    using namespace cma::cfg;
    MrpeProvider mrpe;
    EXPECT_EQ(mrpe.getUniqName(), cma::section::kMrpe);
    auto yaml = GetLoadedConfig();
    ASSERT_TRUE(yaml.IsMap());

    auto mrpe_yaml_optional = GetGroup(yaml, groups::kMrpe);
    ASSERT_TRUE(mrpe_yaml_optional.has_value());
    {
        auto& mrpe_cfg = mrpe_yaml_optional.value();

        ASSERT_TRUE(GetVal(mrpe_cfg, vars::kEnabled, false));
        auto entries = GetArray<std::string>(mrpe_cfg, vars::kMrpeConfig);
        ASSERT_EQ(entries.size(), 0)
            << "check that yml is ok";  // include and check
    }

    replaceYamlSeq(
        groups::kMrpe, vars::kMrpeConfig,
        {
            "check = Codepage 'c:\\windows\\system32\\chcp.com'",
            "check = Console 'c:\\windows\\system32\\mode.com' CON CP /STATUS",
        });

    auto strings = GetArray<std::string>(groups::kMrpe, vars::kMrpeConfig);
    EXPECT_EQ(strings.size(), 2);
    mrpe.parseConfig();
    ASSERT_EQ(mrpe.includes_.size(), 0);
    ASSERT_EQ(mrpe.checks_.size(), 2);

    mrpe.addParsedConfig();
    EXPECT_EQ(mrpe.entries_.size(), 2);
    mrpe.updateSectionStatus();
    auto accu = mrpe.accu_;
    ASSERT_TRUE(!accu.empty());
    auto table = cma::tools::SplitString(accu, "\n");
    ASSERT_EQ(table.size(), 2);

    auto& e0 = mrpe.entries_[0];
    {
        auto hdr =
            fmt::format("({})", e0.exe_name_) + " " + e0.description_ + " 0";
        EXPECT_TRUE(table[0].find(hdr) == 0);
    }
    auto& e1 = mrpe.entries_[1];
    {
        auto hdr =
            fmt::format("({})", e1.exe_name_) + " " + e1.description_ + " 0";
        EXPECT_TRUE(table[1].find(hdr) == 0);
    }
}  // namespace cma::provider

}  // namespace cma::provider
