
// API "Internal transport"

#pragma once
#include <chrono>      // timestamps
#include <cstdint>     // wchar_t when compiler options set weird
#include <functional>  // callback in the main function

#include "common/cfg_info.h"  // default logfile name
#include "common/mailslot_transport.h"
#include "logger.h"
#include "tools/_misc.h"
#include "tools/_xlog.h"

namespace cma::carrier {
enum DataType {
    kLog = 0,
    kSegment = 1,
    kYaml = 2,  // future use
    kCommand = 3
};

// must 4-byte length
constexpr size_t kCarrierNameLength = 4;
constexpr char kCarrierNameDelimiter = ':';
constexpr const char* kCarrierMailslotName = "mail";
constexpr const char* kCarrierGrpcName = "grpc";
constexpr const char* kCarrierAsioName = "asio";
constexpr const char* kCarrierRestName = "rest";
constexpr const char* kCarrierNullName = "null";
constexpr const char* kCarrierFileName = "file";
constexpr const char* kCarrierDumpName = "dump";

inline std::string BuildPortName(const std::string& CarrierName,
                                 const std::string& Address) noexcept {
    return CarrierName + kCarrierNameDelimiter + Address;
}

// #TODO unit test
// Used to send data Provider <-> Agent
// struct is to recall that this is POD
// ctor and dtor are private.
// only method to create is to use "factory method build"
#pragma pack(push, 1)
struct CarrierDataHeader {
    // API:
    enum { kMaxNameLen = 31 };

    using ptr = std::unique_ptr<CarrierDataHeader,
                                std::function<void(CarrierDataHeader*)>>;

    // standard function, which requires ON_OUT_OF SCOPE
    static CarrierDataHeader* createRaw(
        const char* Name,  // usually unique name of provider
        uint64_t Id,       // usually timestamp of the answer to fill
        DataType Type,     // DataType::
        const void* Data,  // data, nullptr is allowed
        uint64_t Length    // data length
        ) noexcept {
        if (strlen(Name) > kMaxNameLen) return nullptr;

        try {
            const auto length = static_cast<size_t>(Length);
            // data payload
            auto block = new char[length + sizeof(CarrierDataHeader)];
            memset(block, 0, +sizeof(CarrierDataHeader));
            auto cdh = reinterpret_cast<CarrierDataHeader*>(block);
            cdh->data_length_ = length;
            if (Data && cdh->data()) {
                memcpy(cdh->data(), Data, length);
            } else
                cdh->data_length_ = 0;  // clean

            // header
            strcpy(cdh->provider_id_, Name);
            memset(cdh->reserved_, 0, sizeof(cdh->reserved_));
            cdh->data_id_ = Id;
            cdh->info_ = 0;
            cdh->type_ = static_cast<DataType>(Type);

            // ready
            return cdh;
        } catch (...) {
            return nullptr;
        }
    }

    // Official API
    // returns unique ptr with custom deleter
    static CarrierDataHeader::ptr createPtr(
        const char* Name,  // usually unique name of provider
        uint64_t Id,       // usually timestamp of the answer to fill
        DataType Type,     // DataType::
        const void* Data,  // data, nullptr is allowed
        uint64_t Length    // data length
        ) noexcept {
        return CarrierDataHeader::ptr(createRaw(Name, Id, Type, Data, Length),
                                      CarrierDataHeader::destroy);
    }

    static void destroy(CarrierDataHeader* Cdh) {
        if (Cdh) delete[] reinterpret_cast<char*>(Cdh);
    }

    const void* data() const {
        auto p = reinterpret_cast<const char*>(this);

        return data_length_ ? static_cast<const void*>(p + sizeof(*this))
                            : nullptr;
    }

    const std::string string() const {
        auto p = reinterpret_cast<const char*>(this);

        auto str = data_length_ ? static_cast<const char*>(p + sizeof(*this))
                                : nullptr;
        if (!str)
            return {};
        else
            return std::string(str, str + data_length_);
    }

    const auto providerId() const { return provider_id_; }
    auto answerId() const { return data_id_; }
    auto length() const { return data_length_; }
    auto fullLength() const { return data_length_ + sizeof(CarrierDataHeader); }
    auto info() const { return info_; }
    auto type() const { return static_cast<DataType>(type_); }

private:
    void* data() {
        auto p = const_cast<char*>(reinterpret_cast<const char*>(this));

        return data_length_ ? static_cast<void*>(p + sizeof(*this)) : nullptr;
    }
    // DATA IS STARTED HERE ****************************************
    char provider_id_[kMaxNameLen + 1];
    uint64_t data_id_;  // find correct answer
    uint64_t type_;     //
    uint64_t info_;     // flags, cached, etc
    uint32_t reserved_[16];

    uint64_t data_length_;
    // DATA ENDED HERE *********************************************
private:
    CarrierDataHeader() {}
    ~CarrierDataHeader() {}
};
#pragma pack(pop)

// Abstraction for transport communication from Client side
// normally for Agent-Provider
// can be used for Agent-Monitor
// THREAD SAFE
class CoreCarrier {
public:
    CoreCarrier() : first_file_write_(true) {}
    virtual ~CoreCarrier() {}

    // BASE API
    bool establishCommunication(const std::string& CarrierName);
    bool sendData(const std::string& PeerName, uint64_t Marker,
                  const void* Data, size_t Length);
    bool sendLog(const std::string& PeerName, const void* Data, size_t Length);
    bool sendCommand(std::string_view peer_name, std::string_view command);
    void shutdownCommunication();

    // Helper API #TODO gtest
    static inline bool FireSend(
        const std::wstring& PeerName,  // assigned by caller
        const std::wstring& Port,      // standard format
        const std::wstring& Id,        // identifies Answer
        const void* Data, size_t Length) {
        using namespace cma::tools;

        auto id = ConvertToUint64(Id);
        if (id.has_value()) {
            std::string port(Port.begin(), Port.end());
            CoreCarrier cc;
            cc.establishCommunication(port);
            auto ret = cc.sendData(ConvertToString(PeerName), id.value(), Data,
                                   Length);
            cc.shutdownCommunication();
            return ret;
        } else {
            XLOG::l("Failed to convert id value '{}'",
                    wtools::ConvertToUTF8(Id));
            return false;
        }
    }

    // Helper API #TODO gtest
    template <typename T>
    static bool FireCommand(const std::wstring& Name, const T& Port,
                            const void* Data, size_t Length) {
        CoreCarrier cc;
        std::string port(Port.begin(), Port.end());
        cc.establishCommunication(port);

        cc.sendLog(cma::tools::ConvertToString(Name), Data, Length);
        cc.shutdownCommunication();
        return true;
    }

    // Helper API #TODO gtest
    template <typename T>
    static bool FireLog(const std::wstring& Name, const T& Port,
                        const void* Data, size_t Length) {
        CoreCarrier cc;
        std::string port(Port.begin(), Port.end());
        cc.establishCommunication(port);

        cc.sendLog(cma::tools::ConvertToString(Name), Data, Length);
        cc.shutdownCommunication();
        return true;
    }

    // Helper API #TODO gtest
    template <typename T, typename... Args>
    static bool FireLogX(const std::wstring& Name, const T& Port,
                         const Args&... args) {
        std::string buffer = fmt::formatv(args...);
        /*
                auto x = std::make_tuple(args...);
                auto print_message = [&buffer](const auto&... args) {
                    // return formatted value
                    buffer = fmt::format(args...);
                };
                std::apply(print_message, x);
        */
        return FireLog(Name, Port, buffer.c_str(), buffer.length());
    }

private:
    bool sendDataDispatcher(DataType Type, const std::string& PeerName,
                            uint64_t Marker, const void* Data, size_t Length);
    bool mailSlotSend(DataType Type, const std::string& PeerName,
                      uint64_t Marker, const void* Data, size_t Length);
    bool dumpSlotSend(DataType Type, const std::string& PeerName,
                      uint64_t Marker, const void* Data, size_t Length);
    bool fileSlotSend(DataType Type, const std::string& PeerName,
                      uint64_t Marker, const void* Data, size_t Length);
    bool nullSlotSend(DataType Type, const std::string& PeerName,
                      uint64_t Marker, const void* Data, size_t Length);
    bool asioSlotSend(DataType Type, const std::string& PeerName,
                      uint64_t Marker, const void* Data, size_t Length);

    std::mutex lock_;
    std::string carrier_name_;
    std::string carrier_address_;

    bool first_file_write_;  // used for a "file" carrier

    std::function<bool(CoreCarrier* This, DataType Type,
                       const std::string& PeerName, uint64_t Marker,
                       const void* Data, size_t Length)>
        data_sender_ = nullptr;

#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class CarrierTest;
    FRIEND_TEST(CarrierTest, Mail);
    FRIEND_TEST(CarrierTest, EstablishShutdown);
#endif
};

};  // namespace cma::carrier
