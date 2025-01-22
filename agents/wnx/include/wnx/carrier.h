// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// API "Internal transport"

#pragma once
#include <cstdint>     // wchar_t when compiler options set weird
#include <functional>  // callback in the main function

#include "common/wtools.h"  // conversion
#include "logger.h"
#include "tools/_misc.h"

namespace cma::carrier {
enum class DataType {
    kLog = 0,      /// write to log file
    kSegment = 1,  /// write as section data
    kYaml = 2,     /// universal/custom
    kCommand = 3,  /// execute as internal command
};

// must 4-byte length
constexpr size_t kCarrierNameLength = 4;
constexpr char kCarrierNameDelimiter = ':';
constexpr std::string_view kCarrierMailslotName = "mail";
constexpr std::string_view kCarrierGrpcName = "grpc";
constexpr std::string_view kCarrierAsioName = "asio";
constexpr std::string_view kCarrierRestName = "rest";
constexpr std::string_view kCarrierNullName = "null";
constexpr std::string_view kCarrierFileName = "file";
constexpr std::string_view kCarrierDumpName = "dump";

inline std::string BuildPortName(std::string_view carrier_name,
                                 std::string_view address) noexcept {
    return std::string{carrier_name} + kCarrierNameDelimiter +
           std::string{address};
}

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

    /// returns unique ptr with custom deleter
    static ptr createPtr(const char *provider_name,  // unique name of provider
                         uint64_t answer_id,  // timestamp of the answer to fill
                         DataType data_type,  // DataType::
                         const void *data,    // data, nullptr is allowed
                         uint64_t length      // data length
                         ) noexcept {
        return {createRaw(provider_name, answer_id, data_type, data, length),
                destroy};
    }

    [[nodiscard]] const char *asBuf() const noexcept {
        return static_cast<const char *>(static_cast<const void *>(this));
    }

    static void destroy(const CarrierDataHeader *cdh) noexcept {
        if (cdh != nullptr) {
            delete[] cdh->asBuf();
        }
    }

    [[nodiscard]] const void *data() const noexcept {
        const auto *p = asBuf();

        return data_length_ != 0U ? static_cast<const void *>(p + sizeof *this)
                                  : nullptr;
    }

    [[nodiscard]] std::string string() const {
        const auto *p = asBuf();
        const auto *str = data_length_ != 0U ? p + sizeof *this : nullptr;
        if (str == nullptr) {
            return {};
        }
        return std::string{str, static_cast<size_t>(data_length_)};
    }

    [[nodiscard]] auto providerId() const noexcept { return provider_id_; }
    [[nodiscard]] auto answerId() const noexcept { return data_id_; }
    [[nodiscard]] auto length() const noexcept { return data_length_; }
    [[nodiscard]] auto fullLength() const noexcept {
        return data_length_ + sizeof CarrierDataHeader;
    }
    [[nodiscard]] auto info() const noexcept { return info_; }
    [[nodiscard]] auto type() const noexcept {
        return static_cast<DataType>(type_);
    }

private:
    /// - requires ON_OUT_OF SCOPE
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
            auto *block = new char[length + sizeof CarrierDataHeader];
            ::memset(block, 0, +sizeof CarrierDataHeader);
            auto *cdh = reinterpret_cast<CarrierDataHeader *>(block);
            cdh->data_length_ = length;
            if (data != nullptr && cdh->data() != nullptr) {
                memcpy(cdh->data(), data, length);
            } else {
                cdh->data_length_ = 0;  // clean
            }

            // header
            ::strcpy(cdh->provider_id_, provider_name);
            ::memset(cdh->reserved_, 0, sizeof cdh->reserved_);
            cdh->data_id_ = answer_id;
            cdh->info_ = 0;
            cdh->type_ = static_cast<uint64_t>(data_type);

            // ready
            return cdh;
        } catch (...) {
            return nullptr;
        }
    }

    void *data() noexcept {
        auto *p = const_cast<char *>(reinterpret_cast<const char *>(this));

        return data_length_ != 0u ? static_cast<void *>(p + sizeof *this)
                                  : nullptr;
    }
    // DATA IS STARTED HERE ****************************************
    char provider_id_[kMaxNameLen + 1];
    uint64_t data_id_;  // find correct answer
    uint64_t type_;     //
    uint64_t info_;     // flags, cached, etc
    uint32_t reserved_[16];

    uint64_t data_length_;
    // DATA ENDED HERE *********************************************

    CarrierDataHeader() = default;
};
#pragma pack(pop)

// Abstraction for transport communication from Client side
// normally for Agent-Provider
// can be used for Agent-Monitor
// THREAD SAFE
class CoreCarrier {
public:
    // BASE API
    bool establishCommunication(const std::string &internal_port);
    bool sendData(const std::string &peer_name, uint64_t answer_id,
                  const void *data, size_t length);
    bool sendLog(const std::string &peer_name, const void *data, size_t length);
    bool sendCommand(std::string_view peer_name, std::string_view command);
    bool sendYaml(std::string_view peer_name, std::string_view yaml);
    void shutdownCommunication();

    // Accessors
    [[nodiscard]] std::string getName() const noexcept { return carrier_name_; }
    [[nodiscard]] std::string getAddress() const noexcept {
        return carrier_address_;
    }

    static bool FireSend(const std::wstring &peer_name,  // assigned by caller
                         const std::wstring &port_name,  // standard format
                         const std::wstring &answer_id,  // identifies Answer
                         const void *data, size_t length) {
        if (const auto id = tools::ConvertToUint64(answer_id); id.has_value()) {
            const auto port = wtools::ToUtf8(port_name);
            CoreCarrier cc;
            cc.establishCommunication(port);
            const auto ret = cc.sendData(wtools::ToUtf8(peer_name), id.value(),
                                         data, length);
            cc.shutdownCommunication();
            return ret;
        }

        XLOG::l("Failed to convert id value '{}'", wtools::ToUtf8(answer_id));
        return false;
    }

    template <type::AnyStringView S>
    static bool FireCommand(const std::wstring &peer_name, const S &port_name,
                            const void *data, size_t length) {
        CoreCarrier cc;
        auto port = wtools::ToUtf8(port_name);
        cc.establishCommunication(port);

        cc.sendLog(wtools::ToUtf8(peer_name), data, length);
        cc.shutdownCommunication();
        return true;
    }

    template <type::AnyStringView S>
    static bool FireLog(const std::wstring &peer_name, const S &port_name,
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
                      uint64_t answer_id, const void *data,
                      size_t length) const;
    bool dumpSlotSend(DataType data_type, const std::string &peer_name,
                      uint64_t marker, const void *data, size_t length) const;
    bool fileSlotSend(DataType data_type, const std::string &peer_name,
                      uint64_t answer_id, const void *data,
                      size_t length) const;
    bool nullSlotSend(DataType data_type, const std::string &peer_name,
                      uint64_t answer_id, const void *data,
                      size_t length) const;
    bool asioSlotSend(DataType data_type, const std::string &peer_name,
                      uint64_t answer_id, const void *data,
                      size_t length) const;

    std::mutex lock_;
    std::string carrier_name_;
    std::string carrier_address_;

    mutable bool first_file_write_{true};  // used for a "file" carrier

    std::function<bool(CoreCarrier *self, DataType data_type,
                       const std::string &peer_name, uint64_t marker,
                       const void *data, size_t length)>
        data_sender_{nullptr};
};
void InformByMailSlot(std::string_view mail_slot, std::string_view cmd);
std::string AsString(const CarrierDataHeader *dh) noexcept;

std::vector<unsigned char> AsDataBlock(const CarrierDataHeader *dh) noexcept;
}  // namespace cma::carrier
