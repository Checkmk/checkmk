// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2017             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include "OutputProxy.h"
#include <winsock2.h>
#include <cstdarg>
#include "LoggerAdaptor.h"

// urgh
extern volatile bool g_should_terminate;

FileOutputProxy::FileOutputProxy(FILE *file) : _file(file) {}

void FileOutputProxy::output(const char *format, ...) {
    va_list ap;
    va_start(ap, format);
    vfprintf(_file, format, ap);
    va_end(ap);
}

void FileOutputProxy::writeBinary(const char *buffer, size_t size) {
    fwrite(buffer, 1, size, _file);
}

void FileOutputProxy::flush(bool) {
    // nop
}

BufferedSocketProxy::BufferedSocketProxy(
    SOCKET socket, const LoggerAdaptor &logger)
    : _socket(socket), _logger(logger) {
    _buffer.resize(DEFAULT_BUFFER_SIZE);
}

void BufferedSocketProxy::setSocket(SOCKET socket) { _socket = socket; }

void BufferedSocketProxy::output(const char *format, ...) {
    va_list ap;
    va_start(ap, format);

    size_t buffer_left = _buffer.size() - _length;

    int written_len = vsnprintf(&_buffer[0] + _length, buffer_left, format, ap);

    if (written_len >= (int)buffer_left) {
        size_t target_size = _length + written_len + 1;
        size_t new_size = _buffer.size() * 2;
        while (new_size < target_size) {
            new_size *= 2;
        }
        _buffer.resize(new_size);
        vsnprintf(&_buffer[0] + _length, _buffer.size() - _length, format, ap);
    }

    va_end(ap);
    _length += written_len;
}

void BufferedSocketProxy::writeBinary(const char *buffer, size_t size) {
    size_t target_size = _length + size + 1;
    if (_buffer.size() < target_size) {
        size_t new_size = target_size * 2;
        _buffer.resize(new_size);
    }

    memcpy(&_buffer[0] + _length, buffer, size);
    _length += size;
}

void BufferedSocketProxy::flush(bool) {
    int tries = 10;
    while ((_length > 0) && (tries > 0)) {
        --tries;
        if (!flushInt()) {
            return;
        }
        if (_length > 0) {
            ::Sleep(100);
        }
    }
    if (_length > 0) {
        _logger.verbose("failed to flush entire buffer\n");
    }
}

bool BufferedSocketProxy::flushInt() {
    bool error = false;
    size_t offset = 0;
    while (!g_should_terminate) {
        ssize_t result =
            send(_socket, &_buffer[0] + offset, _length - offset, 0);
        if (result == SOCKET_ERROR) {
            int error = WSAGetLastError();
            if (error == WSAEINTR) {
                continue;
            } else if (error == WSAEINPROGRESS) {
                continue;
            } else if (error == WSAEWOULDBLOCK) {
                _logger.verbose("send to socket would block");
                error = true;
                break;
            } else {
                _logger.verbose("send to socket failed with error code %d", error);
                error = true;
                break;
            }
        } else if (result == 0) {
            // nothing written, which means the socket-cache is
            // probably full
        } else {
            offset += result;
        }

        break;
    }
    _length -= offset;
    if ((_length != 0) && (offset != 0)) {
        // not the whole buffer has been sent, shift up the remaining data
        memmove(&_buffer[0], &_buffer[0] + offset, _length);
    }
    return !error;
}

EncryptingBufferedSocketProxy::EncryptingBufferedSocketProxy(
    SOCKET socket, const std::string &passphrase,
    const LoggerAdaptor &logger)
    : BufferedSocketProxy(socket, logger)
    , _crypto(passphrase)
    , _written(0) {
    _blockSize = _crypto.blockSize() / 8;
    _plain.resize(_blockSize * 8);
}

void EncryptingBufferedSocketProxy::output(const char *format, ...) {
    va_list ap;
    va_start(ap, format);

    int buffer_left = _plain.size() - _written;
    int written_len = vsnprintf(&_plain[0] + _written, buffer_left, format, ap);
    if (written_len > buffer_left) {
        _plain.resize(_written + written_len + _blockSize);
        buffer_left = _plain.size() - _written;
        written_len = vsnprintf(&_plain[0] + _written, buffer_left, format, ap);
    }
    va_end(ap);
    _written += written_len;

    if (_written >= _blockSize) {
        // we have at least one block of data. encrypt it and push it to the
        // underlying send buffer
        size_t push_size = (_written / _blockSize) * _blockSize;
        std::vector<char> push_buf(_plain);

        DWORD required_size =
            _crypto.encrypt(NULL, push_size, push_buf.size(), false);
        if (required_size > push_buf.size()) {
            push_buf.resize(required_size);
        }
        _crypto.encrypt(reinterpret_cast<BYTE *>(&push_buf[0]), push_size,
                        push_buf.size(), false);
        writeBinary(&push_buf[0], required_size);

        memmove(&_plain[0], &_plain[push_size], _written - push_size);
        _written -= push_size;
    }
}

void EncryptingBufferedSocketProxy::flush(bool last) {
    // this assumes the plain buffer is large enouph for one measly block
    if (last) {
        char *buffer = &_plain[0];
        DWORD required_size = _crypto.encrypt(reinterpret_cast<BYTE *>(buffer),
                                              _written, _plain.size(), true);
        writeBinary(buffer, required_size);

        _written = 0;
    }

    BufferedSocketProxy::flush(last);
}
