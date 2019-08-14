// data owners  here

#pragma once
namespace cma {
namespace tools {
// ownership belongs to DataBlock
// supplementary structure to store data
// tested in perf_reader.exe(part of the old win agent)
// NOT THREAD SAFE
template <typename T>
struct DataBlock {
    DataBlock() : len_(0), data_(nullptr) {}
    DataBlock(int Size, T* Buffer) : len_(Size), data_(Buffer) {}
    ~DataBlock() { delete[] data_; }

    // no copy:
    DataBlock(const DataBlock&) = delete;
    DataBlock& operator=(const DataBlock&) = delete;

    // default move
    DataBlock(DataBlock&& Rhs) {
        data_ = Rhs.data_;
        len_ = Rhs.len_;
        Rhs.data_ = nullptr;
        Rhs.len_ = 0;
    }

    DataBlock& operator=(DataBlock&& Rhs) {
        delete[] data_;
        data_ = Rhs.data_;
        len_ = Rhs.len_;
        Rhs.data_ = nullptr;
        Rhs.len_ = 0;
        return *this;
    }

    int len_;
    T* data_;
};

}  // namespace tools
}  // namespace cma
