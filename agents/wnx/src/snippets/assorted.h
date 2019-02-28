    // EXAMPLES
void v()
    {
// nice lambda
        auto z = [](auto&... Str) { return std::vector{Str...}; };

        auto zx = z(kDefaultDevConfigFileName, kDefaultConfigFileName);
    }
