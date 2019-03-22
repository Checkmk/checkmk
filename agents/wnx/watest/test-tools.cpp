//
// test-tools.cpp :

#include "pch.h"

#include <filesystem>

#include "common/cfg_info.h"
#include "tools/_misc.h"

#include "cfg.h"
#include "glob_match.h"
#include "test-tools.h"
#include "test-utf-names.h"

namespace tst {
void SafeCleanTempDir() {
    namespace fs = std::filesystem;
    auto temp_dir = cma::cfg::GetTempDir();
    auto normal_dir = temp_dir.find(L"\\temp", 0) != std::wstring::npos;
    if (normal_dir) {
        // clean
        fs::remove_all(cma::cfg::GetTempDir());
        fs::create_directory(temp_dir);
    }
}

void SafeCleanTempDir(const std::string Sub) {
    namespace fs = std::filesystem;
    auto temp_dir = cma::cfg::GetTempDir();
    auto normal_dir = temp_dir.find(L"\\temp", 0) != std::wstring::npos;
    if (normal_dir) {
        // clean
        fs::path t_d = temp_dir;
        fs::remove_all(t_d / Sub);
        fs::create_directory(t_d / Sub);
    } else {
        XLOG::l("attempt to delete suspicious dir {}",
                wtools::ConvertToUTF8(temp_dir));
    }
}

void EnableSectionsNode(const std::string_view& Str, bool UpdateGlobal) {
    using namespace cma::cfg;
    YAML::Node config = GetLoadedConfig();
    {
        YAML::Node enabled = config[groups::kGlobal][vars::kSectionsEnabled];

        bool found = false;
        if (enabled.IsDefined()) {
            // remove from section our name
            for (size_t i = 0; i < enabled.size(); i++) {
                auto node = enabled[i];
                if (node.IsDefined() && node.IsScalar() &&
                    node.as<std::string>() == Str) {
                    found = true;
                    break;
                }
            }

            if (!found) enabled.push_back(std::string(Str));
        }
    }
    YAML::Node disabled = config[groups::kGlobal][vars::kSectionsDisabled];

    {
        if (disabled.IsDefined()) {
            // remove from section our name
            for (size_t i = 0; i < disabled.size(); i++) {
                auto node = disabled[i];
                if (node.IsDefined() && node.IsScalar() &&
                    node.as<std::string>() == Str) {
                    disabled.remove(i);
                    break;
                }
            }
        }
    }
    if (UpdateGlobal) groups::global.loadFromMainConfig();
}
}  // namespace tst

namespace cma::tools {  // to become friendly for cma::cfg classes

TEST(CmaTools, AddVectorsStrings) {
    const std::vector<char> c = {'a', 'b', 'c'};
    const std::vector<char> z = {'x', 'y', 'z'};
    const std::string s = "012";

    {
        auto op = c;
        AddVector(op, z);
        EXPECT_EQ(op.size(), c.size() + z.size());
        auto expected = "abcxyz";
        EXPECT_EQ(0, memcmp(op.data(), expected, op.size()));
    }

    {
        auto str = s;
        AddString(str, z);
        EXPECT_EQ(str.size(), s.size() + z.size());
        auto expected = "012xyz";
        EXPECT_EQ(0, strcmp(str.c_str(), expected));
    }
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

TEST(JoinVectorTest, All) {
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
}

TEST(LowerUpper, All) {
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

TEST(LessTest, AllX) {
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

}  // namespace cma::tools
