//
// test-tools.cpp :

#include "pch.h"

#include "cfg.h"
#include "cma_core.h"
#include "glob_match.h"
#include "test-utf-names.h"
#include "test_tools.h"

namespace cma::tools {
TEST(CmaTools, All) {
    const wchar_t *t[] = {L"a.exe", L"b", L"c"};
    EXPECT_FALSE(CheckArgvForValue(0, t, 0, "a.exe"))
        << "argc == 0 always returns false";
    EXPECT_FALSE(CheckArgvForValue(0, nullptr, 0, "a"))
        << "argv == nullptr always returns false";
    EXPECT_FALSE(CheckArgvForValue(1, nullptr, 1, "b"))
        << "pos >= argc always retursn false";

    EXPECT_TRUE(CheckArgvForValue(2, t, 1, "b"));
    EXPECT_FALSE(CheckArgvForValue(2, t, 2, "c"));
};

}  // namespace cma::tools

namespace cma::tools {  // to become friendly for cma::cfg classes

TEST(CmaTools, AddVectorsStrings) {
    const std::vector<char> c = {'a', 'b', 'c'};
    const std::vector<char> z = {'x', 'y', 'z'};
    const std::string s = "012";

    auto op = c;
    AddVector(op, z);
    EXPECT_EQ(op.size(), c.size() + z.size());
    auto expected = "abcxyz";
    EXPECT_EQ(0, memcmp(op.data(), expected, op.size()));
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
        std::string a = "";
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

TEST(CmaTools, Misc) {
    using namespace std;
    using namespace cma::tools;

    {
        string a_in = "";
        string a_delim = "";
        auto res = SplitString(a_in, a_delim);
        EXPECT_EQ(res.size(), 0);
    }

    {
        string a_in = "";
        string a_delim = "a";
        auto res = SplitString(a_in, a_delim);
        EXPECT_EQ(res.size(), 0);
    }

    {
        string a_in = "abs";
        string a_delim = "";
        auto res = SplitString(a_in, a_delim);
        EXPECT_EQ(res.size(), 1);
        EXPECT_EQ(res[0], "abs");
    }

    {
        string a_in = "abs\n";
        string a_delim = "\n";
        auto res = SplitString(a_in, a_delim);
        EXPECT_EQ(res.size(), 1);
        EXPECT_EQ(res[0], "abs");
    }

    {
        string a_in = "abs\nbda";
        string a_delim = "\n";
        auto res = SplitString(a_in, a_delim);
        EXPECT_EQ(res.size(), 2);
        EXPECT_EQ(res[0], "abs");
        EXPECT_EQ(res[1], "bda");
    }
    {
        string a_in = "abs\n\nbda";
        string a_delim = "\n";

        auto res = SplitString(a_in, a_delim);
        EXPECT_EQ(res.size(), 3);
        EXPECT_EQ(res[0], "abs");
        EXPECT_EQ(res[1], "");
        EXPECT_EQ(res[2], "bda");
    }

    {
        string a_in = "abs\nbda";
        string a_delim = "\n";
        auto res = SplitString(a_in, a_delim, 1);
        EXPECT_EQ(res.size(), 2);
        EXPECT_EQ(res[0], "abs");
        EXPECT_EQ(res[1], "bda");
    }

    {
        string a_in = "abs\nbda";
        string a_delim = "\n";
        auto res = SplitString(a_in, a_delim, 2);
        EXPECT_EQ(res.size(), 2);
        EXPECT_EQ(res[0], "abs");
        EXPECT_EQ(res[1], "bda");
    }

    {
        string a_in = "abs\n\nbda";
        string a_delim = "\n";

        auto res = SplitString(a_in, a_delim, 1);
        EXPECT_EQ(res.size(), 2);
        EXPECT_EQ(res[0], "abs");
        EXPECT_EQ(res[1], "\nbda");
    }

    {
        wstring a_in = L"";
        wstring a_delim = L"";
        auto res = SplitString(a_in, a_delim);
        EXPECT_EQ(res.size(), 0);
    }

    {
        wstring a_in = L"";
        wstring a_delim = L"a";
        auto res = SplitString(a_in, a_delim);
        EXPECT_EQ(res.size(), 0);
    }

    {
        wstring a_in = L"abs";
        wstring a_delim = L"";
        auto res = SplitString(a_in, a_delim);
        EXPECT_EQ(res.size(), 1);
        EXPECT_EQ(res[0], L"abs");
    }

    {
        wstring a_in = L"abs\n";
        wstring a_delim = L"\n";
        auto res = SplitString(a_in, a_delim);
        EXPECT_EQ(res.size(), 1);
        EXPECT_EQ(res[0], L"abs");
    }

    {
        wstring a_in = L"abs\nbda";
        wstring a_delim = L"\n";
        auto res = SplitString(a_in, a_delim);
        EXPECT_EQ(res.size(), 2);
        EXPECT_EQ(res[0], L"abs");
        EXPECT_EQ(res[1], L"bda");
    }
    {
        wstring a_in = L"abs\n\nbda";
        wstring a_delim = L"\n";

        auto res = SplitString(a_in, a_delim);
        EXPECT_EQ(res.size(), 3);
        EXPECT_EQ(res[0], L"abs");
        EXPECT_EQ(res[1], L"");
        EXPECT_EQ(res[2], L"bda");
    }

    {
        wstring a_in = L"abs\nbda";
        wstring a_delim = L"\n";
        auto res = SplitString(a_in, a_delim, 1);
        EXPECT_EQ(res.size(), 2);
        EXPECT_EQ(res[0], L"abs");
        EXPECT_EQ(res[1], L"bda");
    }

    {
        wstring a_in = L"abs\nbda";
        wstring a_delim = L"\n";
        auto res = SplitString(a_in, a_delim, 2);
        EXPECT_EQ(res.size(), 2);
        EXPECT_EQ(res[0], L"abs");
        EXPECT_EQ(res[1], L"bda");
    }

    {
        wstring a_in = L"abs\n\nbda";
        wstring a_delim = L"\n";

        auto res = SplitString(a_in, a_delim, 1);
        EXPECT_EQ(res.size(), 2);
        EXPECT_EQ(res[0], L"abs");
        EXPECT_EQ(res[1], L"\nbda");
    }
}

TEST(Misc, JoinVectorTest) {
    using namespace std;
    {
        vector<wstring> vws = {L"a", L"", L"c"};
        auto ret = JoinVector(vws, L".");
        EXPECT_EQ(ret, L"a..c");
        vector<wstring> vws_empty;
        ret = JoinVector({}, L".");
        EXPECT_EQ(ret, L"");
    }
    {
        vector<string> vws = {"a", "", "c"};
        auto ret = JoinVector(vws, ".");
        EXPECT_EQ(ret, "a..c");
        vector<wstring> vws_empty;
        ret = JoinVector({}, ".");
        EXPECT_EQ(ret, "");
    }
    { EXPECT_EQ(cma::tools::RemoveQuotes("''"), ""); }
}

TEST(Misc, RemoveQuotes) {
    //
    EXPECT_EQ(cma::tools::RemoveQuotes(R"(")"), "\"");
    EXPECT_EQ(cma::tools::RemoveQuotes(R"("''")"), "''");
    EXPECT_EQ(cma::tools::RemoveQuotes(R"("aa")"), "aa");
    EXPECT_EQ(cma::tools::RemoveQuotes(R"("__')"), "__");
    EXPECT_EQ(cma::tools::RemoveQuotes(R"('__")"), "__");
    EXPECT_EQ(cma::tools::RemoveQuotes(R"('__')"), "__");
    EXPECT_EQ(cma::tools::RemoveQuotes(R"("aa")"), "aa");

    //
    EXPECT_EQ(cma::tools::RemoveQuotes(LR"(")"), L"\"");
    EXPECT_EQ(cma::tools::RemoveQuotes(LR"("''")"), L"''");
    EXPECT_EQ(cma::tools::RemoveQuotes(LR"("aa")"), L"aa");
    EXPECT_EQ(cma::tools::RemoveQuotes(LR"("__')"), L"__");
    EXPECT_EQ(cma::tools::RemoveQuotes(LR"('__")"), L"__");
    EXPECT_EQ(cma::tools::RemoveQuotes(LR"('__')"), L"__");
    EXPECT_EQ(cma::tools::RemoveQuotes(LR"("aa")"), L"aa");
}

TEST(Misc, LowerUpper) {
    {
        std::wstring w = test_cyrillic;
        cma::tools::WideUpper(w);
        std::wstring w_u = test_cyrillic_upper;
        EXPECT_EQ(w, w_u);
    }
    {
        std::wstring w = L"";
        cma::tools::WideUpper(w);
        EXPECT_EQ(w, L"");
    }

    {
        std::wstring w = test_cyrillic;
        cma::tools::WideLower(w);
        std::wstring w_l = test_cyrillic_lower;
        EXPECT_EQ(w, w_l);
    }
    {
        std::wstring w = L"";
        cma::tools::WideLower(w);
        EXPECT_EQ(w, L"");
    }
}

TEST(Misc, LessTest) {
    {
        EXPECT_TRUE(false == IsLess("a", ""));
        EXPECT_TRUE(false == IsLess("aa", "a"));

        EXPECT_TRUE(true == IsLess("a", "b"));
        EXPECT_TRUE(false == IsLess("b", "a"));

        EXPECT_TRUE(false == IsLess("b", "b"));

        EXPECT_TRUE(true == IsLess("a", "aa"));
        EXPECT_TRUE(true == IsLess("aa", "AAa"));

        EXPECT_TRUE(false == IsLess("b", "A"));

        EXPECT_TRUE(false == IsLess("b", "B"));
    }

    {
        EXPECT_TRUE(false == IsEqual("a", ""));
        EXPECT_TRUE(false == IsEqual("aa", "a"));
        EXPECT_TRUE(false == IsEqual("a", "b"));
        EXPECT_TRUE(false == IsEqual("b", "a"));
        EXPECT_TRUE(true == IsEqual("b", "b"));
        EXPECT_TRUE(false == IsEqual("a", "aa"));
        EXPECT_TRUE(false == IsEqual("aa", "AAa"));
        EXPECT_TRUE(false == IsEqual("b", "A"));
        EXPECT_TRUE(true == IsEqual("b", "B"));
    }
}

TEST(CmaTools, StringCache) {
    {
        tools::StringSet cache;
        ASSERT_TRUE(cache.size() == 0);
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
}

namespace win {
TEST(Misc, WithEnv) {
    std::string env_var_name = "XxYyZz_1";
    std::string env_var_value = "aaa";
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
