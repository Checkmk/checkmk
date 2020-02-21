// watest.cpp : This file contains the 'main' function. Program execution begins
// and ends there.
//
#include "pch.h"

#include <fmt/format.h>
#include <shellapi.h>

#include <iterator>

#include "cfg.h"
#include "modules.h"

namespace cma::tools {
template <typename T, typename = void>
struct is_iterable : std::false_type {};

// this gets used only when we can call std::begin() and std::end() on that type
template <typename T>
struct is_iterable<T, std::void_t<decltype(std::begin(std::declval<T>())),
                                  decltype(std::end(std::declval<T>()))>>
    : std::true_type {};

// Here is a helper:
template <typename T>
constexpr bool is_iterable_v = is_iterable<T>::value;
}  // namespace cma::tools

namespace cma::cfg::modules {

template <typename T>
bool Compare(const T &t, const T &v) {
    static_assert(cma::tools::is_iterable<T>::value);
    if (t.size() != v.size()) return false;

    return std::equal(t.begin(), t.end(), v.begin());
}

TEST(ModulesTest, Internal) {
    Module m;
    EXPECT_FALSE(m.valid());
    EXPECT_TRUE(m.exec().empty());
    EXPECT_TRUE(m.exts().empty());
    EXPECT_TRUE(m.name().empty());
    EXPECT_TRUE(m.exec_.empty());
    EXPECT_TRUE(m.exts_.empty());
    EXPECT_TRUE(m.name_.empty());

    m.exec_ = L"a";
    m.exts_.emplace_back("v");
    m.name_ = "z";
    EXPECT_EQ(m.exec(), L"a");
    EXPECT_EQ(m.name(), "z");
    EXPECT_TRUE(Compare(m.exts(), {"v"}));
    EXPECT_TRUE(m.valid());

    // reset test
    m.reset();
    EXPECT_FALSE(m.valid());
    EXPECT_TRUE(m.exec().empty());
    EXPECT_TRUE(m.exts().empty());
    EXPECT_TRUE(m.name().empty());
}

struct TestSet {
    std::string name;
    std::string exts;
    std::string exec;
    std::string dir;
};

TEST(ModulesTest, Loader) {
    TestSet bad_sets[] = {
        //
        {{}, {}, {}, {}},
        {{""}, {"[e1]"}, {"x"}, {""}},
        {{}, {"[e1]"}, {"x"}, {"dir: m\\{}"}},
        //
    };
    TestSet good_sets[] = {
        //
        {"the-1.0", "[.e1, .e2]", "x", "dir: modules\\{}"},  // full
        {"the-1.0", "[.e1]", "x", "dir: "},                  // empty dir
        {"the-1.0", "[.e1]", "x", ""},                       // empty dir
        //
    };

    constexpr std::string_view base =
        "name: {}\n"
        "exts: {}\n"
        "exec: {}\n"
        "{}\n";

    for (auto s : good_sets) {
        Module m;
        auto text = fmt::format(base, s.name, s.exts, s.exec, s.dir);
        auto node = YAML::Load(text);
        EXPECT_TRUE(m.loadFrom(node));
        EXPECT_TRUE(m.valid());
        EXPECT_EQ(m.name(), s.name);
        auto arr = cma::cfg::GetArray<std::string>(YAML::Load(s.exts));
        EXPECT_TRUE(Compare(m.exts(), arr));
        EXPECT_EQ(m.exec(), wtools::ConvertToUTF16(s.exec));
        if (s.dir.size() <= 5)
            EXPECT_EQ(m.dir(), fmt::format(defaults::kModulesDir, m.name()));
        else
            EXPECT_EQ(m.dir(), fmt::format(s.dir.c_str() + 5, m.name()));
    }

    for (auto s : bad_sets) {
        Module m;
        auto text = fmt::format(base, s.name, s.exts, s.exec, s.dir);
        auto node = YAML::Load(text);
        EXPECT_FALSE(m.loadFrom(node));
        EXPECT_FALSE(m.valid());
        EXPECT_TRUE(m.exec().empty());
        EXPECT_TRUE(m.exts().empty());
        EXPECT_TRUE(m.name().empty());
        EXPECT_TRUE(m.dir().empty());
    }
}

TEST(ModulesTest, TableLoader) {
    std::string work_set[7] = {
        "the",  "['.a', '.b']", "x",           //
        "the2", "['.a']",       "x2", "m\\{}"  //
    };

    constexpr std::string_view base =
        "modules:\n"
        "  enabled: {0}\n"
        "  table:\n"
        "    - name: {1}\n"           // valid
        "      exts: {2}\n"           //
        "      exec: {3}\n"           //
        "    - name: {1}\n"           // duplicated
        "      exts: {2}\n"           //
        "      exec: {3}\n"           //
        "    - name: \n"              // invalid
        "      exts: ['.a', '.b']\n"  //
        "      exec: z\n"             //
        "    - name: {4}\n"           // valid
        "      exts: {5}\n"           //
        "      exec: {6}\n"           //
        "      dir: {7}\n";           //

    {
        Module m;
        {
            auto text =
                fmt::format(base, "No", work_set[0], work_set[1], work_set[2],
                            work_set[3], work_set[4], work_set[5], work_set[6]);
            auto config = YAML::Load(text);
            auto modules = LoadFromConfig(config);
            ASSERT_TRUE(modules.empty());
        }
        {
            auto text =
                fmt::format(base, "Yes", work_set[0], work_set[1], work_set[2],
                            work_set[3], work_set[4], work_set[5], work_set[6]);
            auto config = YAML::Load(text);
            auto modules = LoadFromConfig(config);
            ASSERT_EQ(modules.size(), 2);
            EXPECT_EQ(modules[0].name(), "the");
            EXPECT_EQ(modules[1].name(), "the2");
            EXPECT_EQ(modules[0].exec(), L"x");
            EXPECT_EQ(modules[1].exec(), L"x2");
            EXPECT_TRUE(Compare(modules[0].exts(),
                                std::vector<std::string>{".a", ".b"}));
            EXPECT_TRUE(
                Compare(modules[1].exts(), std::vector<std::string>{".a"}));
            EXPECT_EQ(modules[0].dir(), "modules\\the");
            EXPECT_EQ(modules[1].dir(), "m\\the2");
        }
    }
}

}  // namespace cma::cfg::modules
