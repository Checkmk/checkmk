//
// test-tools.cpp :

#include "pch.h"

#include "watest/test-utf-names.h"
#include "watest/test_tools.h"
#include "wnx/cfg.h"
#include "wnx/cma_core.h"
#include "wnx/glob_match.h"
#include "wnx/read_file.h"

using namespace std::string_literals;
using namespace std::string_view_literals;

namespace cma::tools {
TEST(CmaTools, CheckArgvForValue) {
    const wchar_t *t[] = {L"a.exe", L"b", L"c"};
    EXPECT_FALSE(CheckArgvForValue(0, t, 0, "a.exe"))
        << "argc == 0 always returns false";
    EXPECT_FALSE(CheckArgvForValue(0, nullptr, 0, "a"))
        << "argv == nullptr always returns false";
    EXPECT_FALSE(CheckArgvForValue(1, nullptr, 1, "b"))
        << "pos >= argc always retursn false";

    EXPECT_TRUE(CheckArgvForValue(2, t, 1, "b"));
    EXPECT_FALSE(CheckArgvForValue(2, t, 2, "c"));
}

}  // namespace cma::tools

namespace cma::tools {  // to become friendly for cma::cfg classes

TEST(CmaTools, AddVectorsStrings) {
    const std::vector c = {'a', 'b', 'c'};
    const std::vector z = {'x', 'y', 'z'};
    const std::string s = "012";

    auto op = c;
    AddVector(op, z);
    EXPECT_EQ(op.size(), c.size() + z.size());
    auto expected = "abcxyz";
    EXPECT_EQ(0, memcmp(op.data(), expected, op.size()));
}

TEST(CmaTools, GetEnv) {
    EXPECT_TRUE(win::GetEnv("PATH").contains("System32"));
    EXPECT_TRUE(win::GetEnv(L"PATH").contains(L"System32"));
}

TEST(CmaTools, Matchers) {
    using namespace cma::tools;

    EXPECT_EQ(gm::MakeQuestionMark<char>(), '?');
    EXPECT_EQ(gm::MakeQuestionMark<wchar_t>(), L'?');

    EXPECT_EQ(gm::MakeStar<char>(), '*');
    EXPECT_EQ(gm::MakeStar<wchar_t>(), L'*');

    EXPECT_EQ(gm::MakeDot<char>(), '.');
    EXPECT_EQ(gm::MakeDot<wchar_t>(), L'.');

    EXPECT_EQ(gm::MakeDollar<char>(), '$');
    EXPECT_EQ(gm::MakeDollar<wchar_t>(), L'$');

    EXPECT_EQ(gm::MakeCap<char>(), '^');
    EXPECT_EQ(gm::MakeCap<wchar_t>(), L'^');

    EXPECT_EQ(gm::MakeBackSlash<char>(), '\\');
    EXPECT_EQ(gm::MakeBackSlash<wchar_t>(), L'\\');

    EXPECT_TRUE(gm::NeedsEscape('\\'));
    EXPECT_TRUE(gm::NeedsEscape('{'));
    EXPECT_TRUE(gm::NeedsEscape('}'));
    EXPECT_TRUE(gm::NeedsEscape('$'));
    EXPECT_TRUE(gm::NeedsEscape('('));
    EXPECT_TRUE(gm::NeedsEscape(')'));
    EXPECT_TRUE(gm::NeedsEscape('+'));
    EXPECT_TRUE(gm::NeedsEscape('.'));
    EXPECT_TRUE(gm::NeedsEscape('['));
    EXPECT_TRUE(gm::NeedsEscape(']'));
    EXPECT_TRUE(gm::NeedsEscape('^'));
    EXPECT_TRUE(gm::NeedsEscape('|'));

    EXPECT_TRUE(gm::NeedsEscape(L'\\'));
    EXPECT_TRUE(gm::NeedsEscape(L'{'));
    EXPECT_TRUE(gm::NeedsEscape(L'}'));
    EXPECT_TRUE(gm::NeedsEscape(L'$'));
    EXPECT_TRUE(gm::NeedsEscape(L'('));
    EXPECT_TRUE(gm::NeedsEscape(L')'));
    EXPECT_TRUE(gm::NeedsEscape(L'+'));
    EXPECT_TRUE(gm::NeedsEscape(L'.'));
    EXPECT_TRUE(gm::NeedsEscape(L'['));
    EXPECT_TRUE(gm::NeedsEscape(L']'));
    EXPECT_TRUE(gm::NeedsEscape(L'^'));
    EXPECT_TRUE(gm::NeedsEscape(L'|'));

    {
        const std::string to_escape_const = "$()+.[]^{|}";
        std::string to_escape = to_escape_const;
        gm::InsertEscapes(to_escape);
        EXPECT_EQ(to_escape, "\\$\\(\\)\\+\\.\\[\\]\\^\\{\\|\\}");
    }
}

TEST(CmaTools, Trimmer) {
    {
        std::string a = "  a b  ";
        LeftTrim(a);
        EXPECT_EQ(a, "a b  ");
    }
    {
        std::string a = " a ";
        RightTrim(a);
        EXPECT_EQ(a, " a");
    }
    {
        std::string a = " a b ";
        AllTrim(a);
        EXPECT_EQ(a, "a b");
    }

    {
        std::string a;
        LeftTrim(a);
        EXPECT_EQ(a, "");
        RightTrim(a);
        EXPECT_EQ(a, "");
        AllTrim(a);
        EXPECT_EQ(a, "");
    }

    {
        std::string a = "12345";
        LeftTrim(a);
        EXPECT_EQ(a, "12345");
        RightTrim(a);
        EXPECT_EQ(a, "12345");
        AllTrim(a);
        EXPECT_EQ(a, "12345");
    }
}

struct SplitTest {
    std::string in;
    std::string delim;
    std::vector<std::string> expected;
    std::optional<int> count;
};

std::vector<std::string> SplitStringCall(const SplitTest &t) {
    return t.count.has_value() ? SplitString(t.in, t.delim, *t.count)
                               : SplitString(t.in, t.delim);
}

std::vector<std::wstring> SplitStringCallWide(const SplitTest &t) {
    return t.count.has_value()
               ? SplitString(wtools::ConvertToUtf16(t.in),
                             wtools::ConvertToUtf16(t.delim), *t.count)
               : SplitString(wtools::ConvertToUtf16(t.in),
                             wtools::ConvertToUtf16(t.delim));
}

std::vector<std::wstring> ToUtf16(const std::vector<std::string> &strings) {
    std::vector<std::wstring> wstrings;
    std::ranges::transform(
        strings, std::back_inserter(wstrings),
        [](const auto &s) { return wtools::ConvertToUtf16(s); });
    return wstrings;
}

TEST(CmaTools, SplitString) {
    std::vector<SplitTest> tests = {
        {"", "", {}, std::nullopt},
        {"", "a", {}, std::nullopt},
        {"abs\nbda", "\n", {"abs", "bda"}, std::nullopt},
        {"abs\n\nbda", "\n", {"abs", "", "bda"}, std::nullopt},
        {"abs\nbda", "\n", {"abs", "bda"}, 1},
        {"abs\nbda", "\n", {"abs", "bda"}, 2},
        {"abs\n\nbda", "\n", {"abs", "\nbda"}, 1},
    };
    for (const auto &t : tests) {
        EXPECT_EQ(SplitStringCall(t), t.expected);
        EXPECT_EQ(SplitStringCallWide(t), ToUtf16(t.expected));
    }
}

TEST(CmaTools, JoinVector) {
    EXPECT_EQ(JoinVector({L"a", L"", L"c"}, L"."), L"a..c");
    EXPECT_EQ(JoinVector({}, L"."), L"");
    EXPECT_EQ(JoinVector({"a", "", "c"}, "."), "a..c");
    EXPECT_EQ(JoinVector({}, "."), "");
}

TEST(CmaTools, RemoveQuotes) {
    std::vector<std::pair<std::string, std::string>> tests = {
        {R"('')", ""},     {R"(")", "\""},    {R"("''")", "''"},
        {R"("aa")", "aa"}, {R"("__')", "__"}, {R"('__")", "__"},
        {R"('__')", "__"}, {R"("aa")", "aa"},
    };
    for (const auto &[value, expected] : tests) {
        EXPECT_EQ(RemoveQuotes(value), expected);
        EXPECT_EQ(RemoveQuotes(wtools::ConvertToUtf16(value)),
                  wtools::ConvertToUtf16(expected));
    }
}

TEST(CmaTools, WideUpper) {
    std::wstring w = test_cyrillic;
    WideUpper(w);
    EXPECT_EQ(w, test_cyrillic_upper);

    std::wstring nothing;
    WideUpper(nothing);
    EXPECT_EQ(nothing, L"");
}

TEST(CmaTools, WideLower) {
    std::wstring w = test_cyrillic;
    WideLower(w);
    EXPECT_EQ(w, test_cyrillic_lower);

    std::wstring nothing;
    WideLower(w);
    EXPECT_EQ(nothing, L"");
}

TEST(CmaTools, IsLess) {
    EXPECT_FALSE(IsLess("a", ""));
    EXPECT_FALSE(IsLess("aa", "a"));
    EXPECT_TRUE(IsLess("a", "b"));
    EXPECT_FALSE(IsLess("b", "a"));
    EXPECT_FALSE(IsLess("b", "b"));
    EXPECT_TRUE(IsLess("a", "aa"));
    EXPECT_TRUE(IsLess("aa", "AAa"));
    EXPECT_FALSE(IsLess("b", "A"));
    EXPECT_FALSE(IsLess("b", "B"));
    EXPECT_FALSE(IsEqual("a", ""));
    EXPECT_FALSE(IsEqual("aa", "a"));
    EXPECT_FALSE(IsEqual("a", "b"));
    EXPECT_FALSE(IsEqual("b", "a"));
    EXPECT_TRUE(IsEqual("b", "b"));
    EXPECT_FALSE(IsEqual("a", "aa"));
    EXPECT_FALSE(IsEqual("aa", "AAa"));
    EXPECT_FALSE(IsEqual("b", "A"));
    EXPECT_TRUE(IsEqual("b", "B"));
}

TEST(CmaTools, StringCache) {
    tools::StringSet cache;
    EXPECT_TRUE(tools::AddUniqStringToSetIgnoreCase(cache, "aAaaa"));
    ASSERT_TRUE(cache.size() == 1);
    EXPECT_FALSE(tools::AddUniqStringToSetIgnoreCase(cache, "AAaaa"));
    ASSERT_TRUE(cache.size() == 1);

    EXPECT_TRUE(tools::AddUniqStringToSetIgnoreCase(cache, "bcd"));
    ASSERT_TRUE(cache.size() == 2);
    EXPECT_TRUE(tools::AddUniqStringToSetIgnoreCase(cache, "bcd-1"));
    ASSERT_TRUE(cache.size() == 3);
    EXPECT_FALSE(tools::AddUniqStringToSetIgnoreCase(cache, "AAaaa"));
    ASSERT_TRUE(cache.size() == 3);

    EXPECT_FALSE(tools::AddUniqStringToSetAsIs(cache, "AAAAA"));
    ASSERT_TRUE(cache.size() == 3);
    EXPECT_TRUE(tools::AddUniqStringToSetAsIs(cache, "AAaaA"));
    ASSERT_TRUE(cache.size() == 4);
}

TEST(CmaTools, ToView) {
    EXPECT_EQ(ToView(L"a"s), "a\x0"sv);
    EXPECT_EQ(ToView("A\0Z\x0"s), "A\0Z\0"sv);
    const std::vector data = {L'A', L'b', L'c'};
    EXPECT_EQ(ToView(data), "A\0b\0c\0"sv);
}

TEST(CmaTools, ToWideView) {
    EXPECT_FALSE(ToWideView("a"s).has_value());
    const auto result = *ToWideView("\xD6\0\n\0"sv);
    const auto expected = wtools::ConvertToUtf16("Ö\n"sv);
    EXPECT_EQ(result, expected);
}

TEST(CmaTools, ScanView) {
    constexpr auto haystack{"markline2mark markline4markz"sv};
    constexpr auto needle{"mark"sv};
    std::vector<std::string> result;
    const std::vector<std::string> expected = {"mark", "line2mark", " mark",
                                               "line4mark", "z"};

    ScanView(haystack, needle,
             [&](auto s) { result.emplace_back(std::string{s}); });
    EXPECT_EQ(result, expected);
}

namespace {
std::vector<char> JoinBomLe(std::wstring_view value) {
    constexpr auto bom{"\xFF\xFE"sv};
    std::vector<char> data;
    data.assign(bom.begin(), bom.end());
    const auto begin = reinterpret_cast<const char *>(value.data());
    data.append_range(std::vector<char>{begin, begin + value.size() * 2});
    return data;
}
}  // namespace

std::pair<std::vector<char>, std::string> GetGoodTestPair() {
    constexpr auto expected_result = "ÜÖÄa\nФИФИ"sv;
    const auto in = wtools::ConvertToUtf16(expected_result);
    const auto good_input = JoinBomLe(in);
    return {good_input, std::string{expected_result}};
}

std::pair<std::vector<char>, std::string> GetBadTestPairMix_Odd_16_Odd() {
    std::vector<char> bad{
        '\xFF', '\xFE',             //
        'A',    'B',    'C',        // "ABC"
        '\x0A', '\0',               // \n
        'A',    '\0',   'B', '\0',  // L"AB"
        '\x0A', '\0',               // \n
        'A',    'B',    'C',        // "ABC"
    };
    return {bad, std::string{"ABC\nAB\nABC"s}};
}
TEST(CmaTools, ConvertUtfDataGood) {
    const auto [good, expected] = GetGoodTestPair();
    EXPECT_EQ(ConvertUtfData(good, basic), expected);
    EXPECT_EQ(ConvertUtfData(good, repair_by_line), expected);
}

TEST(CmaTools, ConvertUtfDataGetBadTestPairMix_Odd_16_Odd) {
    const auto [bad_input, expected] = GetBadTestPairMix_Odd_16_Odd();

    EXPECT_NE(ConvertUtfData(bad_input, basic), expected);
    EXPECT_EQ(ConvertUtfData(bad_input, repair_by_line), expected);
}

auto GetBadUtfMix() -> std::vector<char> {
    const auto file_data = ReadFileInVector(tst::MakePathToUnitTestFiles() /
                                            "utf_16_mix_16_8_16.txt");
    const auto raw_data = reinterpret_cast<const char *>(file_data->data());
    return {raw_data, raw_data + file_data->size()};
}

// Special test to check repairing of UTF
TEST(CmaTools, ConvertUtfDataUsingUtfMixIntegration) {
    // consists from UTF0-16 UTF-8 mix
    const auto data = GetBadUtfMix();
    ASSERT_FALSE(data.empty());
    const auto converted_1 = ConvertUtfData(data, basic);
    EXPECT_TRUE(converted_1.empty());
    const auto converted_2 = ConvertUtfData(data, repair_by_line);
    EXPECT_EQ(converted_2.size(), 270U);
    XLOG::l("{}", converted_2);
}

namespace win {
TEST(CmaToolsWin, WithEnv) {
    const std::string env_var_name = "XxYyZz_1";
    const std::string env_var_value = "aaa";
    EXPECT_EQ(GetEnv(env_var_name), "");
    {
        WithEnv with_env(env_var_name, env_var_value);
        EXPECT_EQ(GetEnv(env_var_name), env_var_value);
        EXPECT_EQ(with_env.name(), env_var_name);
        auto w_e = std::move(with_env);
        EXPECT_EQ(GetEnv(env_var_name), env_var_value);
        EXPECT_TRUE(with_env.name().empty());
        EXPECT_EQ(w_e.name(), env_var_name);
        auto w_e2(std::move(w_e));
        EXPECT_EQ(GetEnv(env_var_name), env_var_value);
        EXPECT_TRUE(w_e.name().empty());
        EXPECT_EQ(w_e2.name(), env_var_name);
    }
    EXPECT_EQ(GetEnv(env_var_name), "");
}

}  // namespace win

}  // namespace cma::tools
