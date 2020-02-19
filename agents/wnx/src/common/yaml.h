//
// Partial support for string_view in YAML CPP
// No C++ file
#pragma once

#include <yaml-cpp/yaml.h>

#include <string>
#include <string_view>

namespace YAML {
template <>
inline const Node Node::operator[](const std::string_view& key) const {
    //
    return operator[](std::string(key));
}

template <>
inline Node Node::operator[](const std::string_view& key) {
    //
    return operator[](std::string(key));
}

template <>
inline bool Node::remove(const std::string_view& key) {
    //
    return remove(std::string(key));
}

}  // namespace YAML
