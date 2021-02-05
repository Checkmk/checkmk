#include "stdafx.h"

#include "carrier.h"

#include <algorithm>
#include <iostream>

#include "commander.h"
#include "common/mailslot_transport.h"
#include "logger.h"
#include "tools/_misc.h"

namespace cma::carrier {

static const std::vector<std::string> S_SupportedCarriers = {
    kCarrierMailslotName,  // standard internal
    kCarrierNullName,      // drop
    kCarrierDumpName,      // log only
    kCarrierFileName       // write to file
};

static const std::vector<std::string> S_UnsupportedCarriers = {
    kCarrierAsioName,  // future use
};

static auto ParseInternalPort(const std::string& internal_port) {
    return cma::tools::ParseKeyValue(internal_port, kCarrierNameDelimiter);
}

// BASE API

// gtest[+]
bool CoreCarrier::establishCommunication(const std::string& internal_port) {
    using namespace cma::carrier;

    std::lock_guard lk(lock_);
    if (!carrier_name_.empty()) {
        XLOG::l("Empty name of InternalPort is not allowed");
        return false;
    }

    auto [carrier_name, carrier_address] = ParseInternalPort(internal_port);

    // find a value in a vector
    auto finder = [](const auto& tbl, const auto& val) -> bool {
        return std::find(tbl.begin(), tbl.end(), val) != std::end(tbl);
    };

    if (finder(S_SupportedCarriers, carrier_name)) {
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
            // this is ok for null devices for example
            data_sender_ = nullptr;
        }
        return true;
    }

    if (finder(S_UnsupportedCarriers, carrier_name)) {
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

// BASE API
// gtest [+]
bool CoreCarrier::sendData(const std::string& PeerName, uint64_t Marker,
                           const void* Data, size_t Length) {
    std::lock_guard lk(lock_);
    XLOG::d.t("Sending data '{}' id is [{}] length [{}]", PeerName, Marker,
              Length);
    return sendDataDispatcher(DataType::kSegment, PeerName, Marker, Data,
                              Length);
}

// BASE API
bool CoreCarrier::sendLog(const std::string& PeerName, const void* Data,
                          size_t Length) {
    std::lock_guard lk(lock_);
    return sendDataDispatcher(DataType::kLog, PeerName, 0, Data, Length);
}

bool CoreCarrier::sendCommand(std::string_view peer_name,
                              std::string_view command) {
    std::lock_guard lk(lock_);
    return sendDataDispatcher(DataType::kCommand, std::string(peer_name), 0,
                              command.data(), command.size());
}

// gtest [+]
void CoreCarrier::shutdownCommunication() {
    using namespace cma::carrier;
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
// Data may be nullptr
// PeerName is name of plugin
bool CoreCarrier::sendDataDispatcher(DataType Type, const std::string& PeerName,
                                     uint64_t Marker, const void* Data,
                                     size_t Length) {
    using namespace cma::carrier;

    // data_sender_ is a functor which sets during establishConnection
    if (data_sender_)
        return data_sender_(this, Type, PeerName, Marker, Data, Length);
    return false;
}

// #TODO Unit tests!
bool CoreCarrier::mailSlotSend(DataType Type, const std::string& PeerName,
                               uint64_t Marker, const void* Data,
                               size_t Length) {
    cma::MailSlot postman(carrier_address_.c_str());
    auto cdh = CarrierDataHeader::createPtr(PeerName.c_str(), Marker, Type,
                                            Data, Length);
    if (!cdh) {
        XLOG::l("Cannot create data for peer {} length {}", PeerName, Length);
        return false;
    }

    auto ret = postman.ExecPost(cdh.get(), cdh->fullLength());
    if (!ret) {
        XLOG::l("Failed to send data to mail slot");
    }
    return ret;
}

bool CoreCarrier::dumpSlotSend(DataType type, const std::string& peer_name,
                               uint64_t marker, const void* data_in,
                               size_t length)

{
    auto data = static_cast<const char*>(data_in);
    if (data) {
        if (type == kSegment)
            std::cout << data;
        else
            std::cerr << data << '\n';
    }
    return true;
}

bool CoreCarrier::fileSlotSend(DataType Type, const std::string& PeerName,
                               uint64_t Marker, const void* Data,
                               size_t Length) {
    try {
        std::ofstream f;
        switch (Type) {
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
                std::string cmd(static_cast<const char*>(Data), Length);
                auto rcp = cma::commander::ObtainRunCommandProcessor();
                if (rcp) rcp(PeerName, cmd);
            } break;

            default:
                f.open(carrier_address_ + ".unknown",
                       std::ios::app | std::ios::binary);
                break;
        }

        if (Data) {
            auto data = static_cast<const char*>(Data);
            f.write(data, Length);
            if (Type == kLog) {
                char c = '\n';
                f.write(&c, 1);
            }
        }
        f.close();
    } catch (const std::exception& e) {
        xlog::l(XLOG_FLINE + " Bad exception %s", e.what());
    }

    return true;
}

// nothing
bool CoreCarrier::nullSlotSend(DataType, const std::string&, uint64_t,
                               const void*, size_t) {
    return true;
}

// nothing
bool CoreCarrier::asioSlotSend(DataType, const std::string&, uint64_t,
                               const void*, size_t) {
    return false;
}

void InformByMailSlot(std::string_view mail_slot, std::string_view cmd) {
    cma::carrier::CoreCarrier cc;

    using namespace cma::carrier;
    auto internal_port = BuildPortName(kCarrierMailslotName, mail_slot.data());
    auto ret = cc.establishCommunication(internal_port);
    cc.sendCommand(cma::commander::kMainPeer, cmd);

    cc.shutdownCommunication();
}

}  // namespace cma::carrier
