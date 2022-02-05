// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// API "Internal transport"

#pragma once
#include <chrono>      // timestamps
#include <cstdint>     // wchar_t when compiler options set weird
#include <functional>  // callback in the main function

#include "common/cfg_info.h"  // default logfile name
#include "common/wtools.h"    // conversion
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
constexpr const char *kCarrierMailslotName = "mail";
constexpr const char *kCarrierGrpcName = "grpc";
constexpr const char *kCarrierAsioName = "asio";
constexpr const char *kCarrierRestName = "rest";
constexpr const char *kCarrierNullName = "null";
constexpr const char *kCarrierFileName = "file";
constexpr const char *kCarrierDumpName = "dump";

inline std::string BuildPortName(const std::string &carrier_name,
                                 const std::string &address) noexcept {
    return carrier_name + kCarrierNameDelimiter + address;
}

// #TODO unit test
// Used to send data Provider <-> Agent
// struct is to recall that this is POD
// ctor and dtor are private.
// only method to create is to use "factory method build"
#pragma pack(push, 1)
struct CarrierDataHeader {
    // API:
    static constexpr size_t kMaxNameLen{31};

    using ptr = std::unique_ptr<CarrierDataHeader,
                                std::function<void(CarrierDataHeader *)>>;

    /// \brief returns unique ptr with custom deleter
    static CarrierDataHeader::ptr createPtr(
        const char *provider_name,  // unique name of provider
        uint64_t answer_id,         // timestamp of the answer to fill
        DataType data_type,         // DataType::
        const void *data,           // data, nullptr is allowed
        uint64_t length             // data length
        ) noexcept {
        return CarrierDataHeader::ptr(
            createRaw(provider_name, answer_id, data_type, data, length),
            CarrierDataHeader::destroy);
    }

    static void destroy(CarrierDataHeader *Cdh) {
        if (Cdh) delete[] reinterpret_cast<char *>(Cdh);
    }

    const void *data() const {
        auto p = reinterpret_cast<const char *>(this);

        return data_length_ ? static_cast<const void *>(p + sizeof(*this))
                            : nullptr;
    }

    const std::string string() const {
        auto p = reinterpret_cast<const char *>(this);

        auto str = data_length_ ? static_cast<const char *>(p + sizeof(*this))
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
    /// \brief - requires ON_OUT_OF SCOPE
    static CarrierDataHeader *createRaw(
        const char *provider_name,  // unique name of provider
        uint64_t answer_id,         // timestamp of the answer
        DataType data_type,         // DataType::
        const void *data,           // data, nullptr is allowed
        uint64_t data_length        // data length
        ) noexcept {
        if (::strlen(provider_name) > kMaxNameLen) {
            return nullptr;
        }

        try {
            const auto length = static_cast<size_t>(data_length);
            // data payload
            auto block = new char[length + sizeof(CarrierDataHeader)];
            ::memset(block, 0, +sizeof(CarrierDataHeader));
            auto cdh = reinterpret_cast<CarrierDataHeader *>(block);
            cdh->data_length_ = length;
            if (data && cdh->data()) {
                memcpy(cdh->data(), data, length);
            } else
                cdh->data_length_ = 0;  // clean

            // header
            ::strcpy(cdh->provider_id_, provider_name);
            ::memset(cdh->reserved_, 0, sizeof(cdh->reserved_));
            cdh->data_id_ = answer_id;
            cdh->info_ = 0;
            cdh->type_ = static_cast<DataType>(data_type);

            // ready
            return cdh;
        } catch (...) {
            return nullptr;
        }
    }

    void *data() {
        auto p = const_cast<char *>(reinterpret_cast<const char *>(this));

        return data_length_ ? static_cast<void *>(p + sizeof(*this)) : nullptr;
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
    bool establishCommunication(const std::string &internal_port);
    bool sendData(const std::string &peer_name, uint64_t answer_id,
                  const void *data, size_t length);
    bool sendLog(const std::string &peer_name, const void *data, size_t length);
    bool sendCommand(std::string_view peer_name, std::string_view command);
    void shutdownCommunication();

    // Accessors
    std::string getName() const noexcept { return carrier_name_; }
    std::string getAddress() const noexcept { return carrier_address_; }

    // Helper API
    static inline bool FireSend(
        const std::wstring &peer_name,  // assigned by caller
        const std::wstring &port_name,  // standard format
        const std::wstring &answer_id,  // identifies Answer
        const void *data, size_t length) {
        auto id = tools::ConvertToUint64(answer_id);
        if (id.has_value()) {
            auto port = wtools::ToUtf8(port_name);
            CoreCarrier cc;
            cc.establishCommunication(port);
            auto ret = cc.sendData(wtools::ToUtf8(peer_name), id.value(), data,
                                   length);
            cc.shutdownCommunication();
            return ret;
        }

        XLOG::l("Failed to convert id value '{}'", wtools::ToUtf8(answer_id));
        return false;
    }

    // Helper API #TODO gtest
    template <typename T>
    static bool FireCommand(const std::wstring &peer_name, const T &port_name,
                            const void *data, size_t length) {
        CoreCarrier cc;
        auto port = wtools::ToUtf8(port_name);
        cc.establishCommunication(port);

        cc.sendLog(wtools::ToUtf8(peer_name), data, length);
        cc.shutdownCommunication();
        return true;
    }

    // Helper API #TODO gtest
    template <typename T>
    static bool FireLog(const std::wstring &peer_name, const T &port_name,
                        const void *data, size_t length) {
        CoreCarrier cc;
        auto port = wtools::ToUtf8(port_name);
        cc.establishCommunication(port);

        cc.sendLog(wtools::ToUtf8(peer_name), data, length);
        cc.shutdownCommunication();
        return true;
    }

private:
    bool sendDataDispatcher(DataType data_type, const std::string &peer_name,
                            uint64_t answer_id, const void *data,
                            size_t length);
    bool mailSlotSend(DataType data_type, const std::string &peer_name,
                      uint64_t answer_id, const void *data, size_t length);
    bool dumpSlotSend(DataType type, const std::string &peer_name,
                      uint64_t marker, const void *data_in, size_t length);
    bool fileSlotSend(DataType data_type, const std::string &peer_name,
                      uint64_t answer_id, const void *data, size_t length);
    bool nullSlotSend(DataType data_type, const std::string &peer_name,
                      uint64_t answer_id, const void *data, size_t length);
    bool asioSlotSend(DataType data_type, const std::string &peer_name,
                      uint64_t answer_id, const void *data, size_t length);

    std::mutex lock_;
    std::string carrier_name_;
    std::string carrier_address_;

    bool first_file_write_;  // used for a "file" carrier

    std::function<bool(CoreCarrier *This, DataType data_type,
                       const std::string &peer_name, uint64_t Marker,
                       const void *data, size_t Length)>
        data_sender_ = nullptr;
};
void InformByMailSlot(std::string_view mail_slot, std::string_view cmd);

};  // namespace cma::carrier
