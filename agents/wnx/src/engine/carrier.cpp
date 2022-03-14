#include "stdafx.h"

#include "carrier.h"

#include <algorithm>
#include <fstream>
#include <iostream>
#include <ranges>

#include "commander.h"
#include "common/mailslot_transport.h"
#include "logger.h"
#include "tools/_misc.h"

namespace rs = std::ranges;

namespace cma::carrier {

static const std::vector<std::string> g_supported_carriers = {
    kCarrierMailslotName,  // standard internal
    kCarrierNullName,      // drop
    kCarrierDumpName,      // log only
    kCarrierFileName       // write to file
};

static const std::vector<std::string> g_unsupported_carriers = {
    kCarrierAsioName,  // future use
};

static auto ParseInternalPort(const std::string &internal_port) {
    return cma::tools::ParseKeyValue(internal_port, kCarrierNameDelimiter);
}

bool CoreCarrier::establishCommunication(const std::string &internal_port) {
    std::lock_guard lk(lock_);
    if (!carrier_name_.empty()) {
        XLOG::l("Empty name of InternalPort is not allowed");
        return false;
    }

    auto [carrier_name, carrier_address] = ParseInternalPort(internal_port);

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

void CoreCarrier::shutdownCommunication() {
    std::lock_guard lk(lock_);
    if (carrier_address_ == kCarrierMailslotName) {
        // nothing todo
    } else if (carrier_address_ == kCarrierAsioName) {
        // close connection
    } else {
    }

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
                               size_t length) {
    cma::MailSlot postman(carrier_address_.c_str());
    auto cdh = CarrierDataHeader::createPtr(peer_name.c_str(), answer_id,
                                            data_type, data, length);
    if (!cdh) {
        XLOG::l("Cannot create data for peer {} length {}", peer_name, length);
        return false;
    }

    auto ret = postman.ExecPost(cdh.get(), cdh->fullLength());
    if (!ret) {
        XLOG::l("Failed to send data to mail slot");
    }
    return ret;
}

bool CoreCarrier::dumpSlotSend(DataType data_type,
                               const std::string & /*peer_name*/,
                               uint64_t /*answer_id*/, const void *data,
                               size_t /*length*/)

{
    if (data != nullptr) {
        std::cout << static_cast<const char *>(data);
        if (data_type != kSegment) {
            std::cerr << '\n';
        }
    }
    return true;
}

bool CoreCarrier::fileSlotSend(DataType data_type, const std::string &peer_name,
                               uint64_t /*answer_id*/, const void *data,
                               size_t length) {
    try {
        std::ofstream f;
        switch (data_type) {
            case kSegment:
                f.open(carrier_address_,
                       first_file_write_ ? std::ios::trunc | std::ios::binary
                                         : std::ios::app | std::ios::binary);
                first_file_write_ = false;
                break;
            case kLog:
                f.open(carrier_address_ + ".log", std::ios::app);
                break;
            case kCommand: {
                std::string cmd(static_cast<const char *>(data), length);
                auto rcp = cma::commander::ObtainRunCommandProcessor();
                if (rcp != nullptr) {
                    rcp(peer_name, cmd);
                }
            } break;

            default:
                f.open(carrier_address_ + ".unknown",
                       std::ios::app | std::ios::binary);
                break;
        }

        if (data != nullptr) {
            f.write(static_cast<const char *>(data), length);
            if (data_type == kLog) {
                char c = '\n';
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
                               size_t /*length*/) {
    return true;
}

// nothing
bool CoreCarrier::asioSlotSend(DataType /*data_type*/,
                               const std::string & /*peer_name*/,
                               uint64_t /*answer_id*/, const void * /*data*/,
                               size_t /*length*/) {
    return false;
}

void InformByMailSlot(std::string_view mail_slot, std::string_view cmd) {
    cma::carrier::CoreCarrier cc;

    auto internal_port = BuildPortName(kCarrierMailslotName, mail_slot.data());
    cc.establishCommunication(internal_port);
    cc.sendCommand(cma::commander::kMainPeer, cmd);

    cc.shutdownCommunication();
}

}  // namespace cma::carrier
