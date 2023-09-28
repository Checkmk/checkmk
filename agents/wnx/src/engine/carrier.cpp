#include "stdafx.h"

#include "wnx/carrier.h"

#include <fstream>
#include <iostream>
#include <ranges>

#include "common/mailslot_transport.h"
#include "tools/_misc.h"
#include "wnx/commander.h"
#include "wnx/logger.h"

namespace rs = std::ranges;

namespace cma::carrier {
std::string AsString(const CarrierDataHeader *dh) noexcept {
    if (dh == nullptr) {
        return {};
    }
    return dh->string();
}

std::vector<unsigned char> AsDataBlock(const CarrierDataHeader *dh) noexcept {
    if (dh == nullptr || dh->data() == nullptr) {
        return {};
    }
    const auto *data_source = static_cast<const uint8_t *>(dh->data());
    const auto *data_end = data_source + dh->length();
    std::vector vectorized_data(data_source, data_end);

    if (!vectorized_data.empty() && vectorized_data.back() == 0) {
        XLOG::l.w("Section '{}' sends null terminated strings",
                  dh->providerId());
        vectorized_data.pop_back();
    }
    return vectorized_data;
}

namespace {
const std::vector g_supported_carriers = {
    std::string{kCarrierMailslotName},  // standard internal
    std::string{kCarrierNullName},      // drop
    std::string{kCarrierDumpName},      // log only
    std::string{kCarrierFileName}       // write to file
};

const std::vector g_unsupported_carriers = {
    std::string{kCarrierAsioName},  // future use
};

auto ParseInternalPort(const std::string &internal_port) {
    return tools::ParseKeyValue(internal_port, kCarrierNameDelimiter);
}
}  // namespace

bool CoreCarrier::establishCommunication(const std::string &internal_port) {
    std::lock_guard lk(lock_);
    if (!carrier_name_.empty()) {
        XLOG::l("Empty name of InternalPort is not allowed");
        return false;
    }

    const auto [carrier_name, carrier_address] =
        ParseInternalPort(internal_port);

    if (rs::find(g_supported_carriers, carrier_name) !=
        g_supported_carriers.end()) {
        carrier_address_ = carrier_address;
        carrier_name_ = carrier_name;
        XLOG::t("We are using {} with address {}", carrier_name,
                carrier_address);
        first_file_write_ = true;
        if (carrier_name_ == kCarrierMailslotName)
            data_sender_ = &CoreCarrier::mailSlotSend;
        else if (carrier_name_ == kCarrierNullName)
            data_sender_ = &CoreCarrier::nullSlotSend;
        else if (carrier_name_ == kCarrierDumpName)
            data_sender_ = &CoreCarrier::dumpSlotSend;
        else if (carrier_name_ == kCarrierFileName)
            data_sender_ = &CoreCarrier::fileSlotSend;
        else {
            // we have no data sender for the supported carrier
            data_sender_ = nullptr;
        }
        return true;
    }

    if (rs::find(g_unsupported_carriers, carrier_name) !=
        g_unsupported_carriers.end()) {
        XLOG::d("Carrier '{}' not supported yet, port '{}'", carrier_name,
                internal_port);
        data_sender_ = &CoreCarrier::asioSlotSend;
    } else {
        XLOG::l.crit("Unknown Name of Carrier '{}' on port '{}'", carrier_name,
                     internal_port);
    }

    carrier_name_ = "";
    carrier_address_ = "";

    return false;
}

bool CoreCarrier::sendData(const std::string &peer_name, uint64_t answer_id,
                           const void *data, size_t length) {
    std::lock_guard lk(lock_);
    XLOG::d.t("Sending data '{}' id is [{}] length [{}]", peer_name, answer_id,
              length);
    return sendDataDispatcher(DataType::kSegment, peer_name, answer_id, data,
                              length);
}

bool CoreCarrier::sendLog(const std::string &peer_name, const void *data,
                          size_t length) {
    std::lock_guard lk(lock_);
    return sendDataDispatcher(DataType::kLog, peer_name, 0, data, length);
}

bool CoreCarrier::sendCommand(std::string_view peer_name,
                              std::string_view command) {
    std::lock_guard lk(lock_);
    return sendDataDispatcher(DataType::kCommand, std::string(peer_name), 0,
                              command.data(), command.size());
}

bool CoreCarrier::sendYaml(std::string_view peer_name, std::string_view yaml) {
    std::lock_guard lk(lock_);
    return sendDataDispatcher(DataType::kYaml, std::string(peer_name), 0,
                              yaml.data(), yaml.size());
}

void CoreCarrier::shutdownCommunication() {
    std::lock_guard lk(lock_);
    carrier_address_ = "";
    carrier_name_ = "";
}

// returns true on successful send
// data may be nullptr
// peer_name is name of plugin
bool CoreCarrier::sendDataDispatcher(DataType data_type,
                                     const std::string &peer_name,
                                     uint64_t answer_id, const void *data,
                                     size_t length) {
    if (data_sender_) {
        return data_sender_(this, data_type, peer_name, answer_id, data,
                            length);
    }
    return false;
}

bool CoreCarrier::mailSlotSend(DataType data_type, const std::string &peer_name,
                               uint64_t answer_id, const void *data,
                               size_t length) const {
    mailslot::Slot postman(carrier_address_);
    const auto cdh = CarrierDataHeader::createPtr(peer_name.c_str(), answer_id,
                                                  data_type, data, length);
    if (!cdh) {
        XLOG::l("Cannot create data for peer {} length {}", peer_name, length);
        return false;
    }

    if (!postman.ExecPost(cdh.get(), cdh->fullLength())) {
        XLOG::l("Failed to send data to mail slot");
        return false;
    }
    return true;
}

bool CoreCarrier::dumpSlotSend(DataType data_type,
                               const std::string & /*peer_name*/,
                               uint64_t /*answer_id*/, const void *data,
                               size_t /*length*/) const {
    if (data != nullptr) {
        std::cout << static_cast<const char *>(data);
        if (data_type != DataType::kSegment) {
            std::cerr << '\n';
        }
    }
    return true;
}

bool CoreCarrier::fileSlotSend(DataType data_type, const std::string &peer_name,
                               uint64_t /*answer_id*/, const void *data,
                               size_t length) const {
    try {
        std::ofstream f;
        switch (data_type) {
            case DataType::kSegment:
                f.open(carrier_address_,
                       first_file_write_ ? std::ios::trunc | std::ios::binary
                                         : std::ios::app | std::ios::binary);
                first_file_write_ = false;
                break;
            case DataType::kLog:
                f.open(carrier_address_ + ".log", std::ios::app);
                break;
            case DataType::kCommand:
                if (const auto rcp = commander::ObtainRunCommandProcessor();
                    rcp != nullptr) {
                    const std::string cmd{static_cast<const char *>(data),
                                          length};
                    rcp(peer_name, cmd);
                }
                break;

            case DataType::kYaml:
                f.open(carrier_address_ + ".unknown",
                       std::ios::app | std::ios::binary);
                break;
        }

        if (data != nullptr) {
            f.write(static_cast<const char *>(data),
                    static_cast<std::streamsize>(length));
            if (data_type == DataType::kLog) {
                constexpr char c = '\n';
                f.write(&c, 1);
            }
        }
    } catch (const std::exception &e) {
        xlog::l(XLOG_FLINE + " Bad exception %s", e.what());
    }

    return true;
}

// nothing
bool CoreCarrier::nullSlotSend(DataType /*data_type*/,
                               const std::string & /*peer_name*/,
                               uint64_t /*answer_id*/, const void * /*data*/,
                               size_t /*length*/) const {
    return true;
}

// nothing
bool CoreCarrier::asioSlotSend(DataType /*data_type*/,
                               const std::string & /*peer_name*/,
                               uint64_t /*answer_id*/, const void * /*data*/,
                               size_t /*length*/) const {
    return false;
}

void InformByMailSlot(std::string_view mail_slot, std::string_view cmd) {
    CoreCarrier cc;

    const auto internal_port = BuildPortName(std::string{kCarrierMailslotName},
                                             std::string{mail_slot});
    cc.establishCommunication(internal_port);
    cc.sendCommand(commander::kMainPeer, cmd);

    cc.shutdownCommunication();
}

}  // namespace cma::carrier
