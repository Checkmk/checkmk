#include <random>
#include <string>

// Next function from:
// https://stackoverflow.com/questions/440133/how-do-i-create-a-random-alpha-numeric-string-in-c

inline std::string random_string(const std::string::size_type length) {
    static auto& chrs =
        "0123456789"
        "abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ";

    thread_local static std::mt19937 rg{std::random_device{}()};
    thread_local static std::uniform_int_distribution<std::string::size_type>
        pick(0, sizeof(chrs) - 2);

    std::string str(length, 0);
    for (auto& c : str) {
        c = chrs[pick(rg)];
    };
    return str;
}
