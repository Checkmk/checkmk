#pragma once
#include <mutex>
#include <string>

namespace cma {
constexpr std::string_view kMainObject = "main";

template <typename T>
class MicroRepo {
public:
    MicroRepo() = default;
    MicroRepo(const MicroRepo&) = delete;
    MicroRepo(const MicroRepo&&) = delete;
    MicroRepo& operator=(const MicroRepo&) = delete;
    MicroRepo& operator=(const MicroRepo&&) = delete;

    ~MicroRepo() {
        std::lock_guard lk(lock_);
        for (auto it = map_.begin(); it != map_.end();) {
            auto val = it->second;
            if (val) val.reset();
            it = map_.erase(it);
        }
    }

    [[deprecated]] std::shared_ptr<T> addObject(const std::string& name,
                                                T* object) {
        if (object == nullptr) return {};

        std::lock_guard lk(lock_);
        map_[name].reset(object);
        return map_[name];
    }

    template <typename... Types>
    std::shared_ptr<T> createObject(const std::string& name, Types... args) {
        std::lock_guard lk(lock_);
        map_[name] = std::make_shared<T>(args...);
        return map_[name];
    }

    std::shared_ptr<T> getObject(const std::string& name) const {
        std::lock_guard lk(lock_);
        auto it = map_.find(name);
        if (it == map_.end()) return nullptr;

        return it->second;
    }

    bool removeObject(const std::string& name) {
        std::lock_guard lk(lock_);

        auto node = map_.extract(name);
        if (node) {
            node.mapped().reset();
            return true;
        }

        return false;
    }

    size_t count() const {
        std::lock_guard lk(lock_);
        return map_.size();
    }

private:
    mutable std::mutex lock_;
    std::unordered_map<std::string, std::shared_ptr<T>> map_;
};
}  // namespace cma
