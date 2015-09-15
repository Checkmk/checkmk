// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2015             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// Copyright by Mathias Kettner and Mathias Kettner GmbH.  All rights reserved.
//
// Check_MK is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.
//
// Check_MK is  distributed in the hope that it will be useful, but
// WITHOUT ANY WARRANTY;  without even the implied warranty of
// MERCHANTABILITY  or  FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU General Public License for more details.
//
// You should have  received  a copy of the  GNU  General Public
// License along with Check_MK.  If  not, email to mk@mathias-kettner.de
// or write to the postal address provided at www.mathias-kettner.de

#include "OutputBuffer.h"
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <stdarg.h>
#include <errno.h>

#include "logger.h"
#include "Query.h"

#define WRITE_TIMEOUT_USEC 100000


OutputBuffer::OutputBuffer()
  : _max_size(INITIAL_OUTPUT_BUFFER_SIZE)
{
    _buffer = (char *)malloc(_max_size);
    _end = _buffer + _max_size;
    reset();
}

OutputBuffer::~OutputBuffer()
{
    free(_buffer);
}

void OutputBuffer::reset()
{
    _writepos = _buffer;
    _response_header = RESPONSE_HEADER_OFF;
    _response_code = RESPONSE_CODE_OK;
    _do_keepalive = false;
    _error_message = "";
}

void OutputBuffer::addChar(char c)
{
    needSpace(1);
    *_writepos++ = c;
}

void OutputBuffer::addString(const char *s)
{
    int l = strlen(s);
    addBuffer(s, l);
}

void OutputBuffer::addBuffer(const char *buf, unsigned len)
{
    needSpace(len);
    memcpy(_writepos, buf, len);
    _writepos += len;
}

void OutputBuffer::needSpace(unsigned len)
{
    if (_writepos + len > _end)
    {
        unsigned s = size();
        unsigned needed = s + len;
        while (_max_size < needed) // double, until enough space
            _max_size *= 2;

        _buffer = (char *)realloc(_buffer, _max_size);
        _writepos = _buffer + s;
        _end = _buffer + _max_size;
    }
}

void OutputBuffer::flush(int fd, int *termination_flag)
{
    if (_response_header == RESPONSE_HEADER_FIXED16)
    {
        const char *buffer = _buffer;
        int s = size();

        // if response code is not OK, output error
        // message instead of data
        if (_response_code != RESPONSE_CODE_OK)
        {
            buffer = _error_message.c_str();
            s = _error_message.size();
        }

        char header[17];
        snprintf(header, sizeof(header), "%03d %11d\n", _response_code, s);
        writeData(fd, termination_flag, header, 16);
        writeData(fd, termination_flag, buffer, s);
    }
    else {
        writeData(fd, termination_flag, _buffer, size());
    }
    reset();
}


void OutputBuffer::writeData(int fd, int *termination_flag, const char *write_from, int to_write)
{
    struct timeval tv;
    while (!*termination_flag && to_write > 0)
    {
        tv.tv_sec  = WRITE_TIMEOUT_USEC / 1000000;
        tv.tv_usec = WRITE_TIMEOUT_USEC % 1000000;

        fd_set fds;
        FD_ZERO(&fds);
        FD_SET(fd, &fds);

        int retval = select(fd + 1, NULL, &fds, NULL, &tv);
        if (retval > 0 && FD_ISSET(fd, &fds)) {
            ssize_t w = write(fd, write_from, to_write);
            if (w < 0) {
                logger(LG_INFO, "Couldn't write %d bytes to client socket: %s", to_write, strerror(errno));
                break;
            }
            else if (w == 0)
                logger(LG_INFO, "Strange: wrote 0 bytes inspite of positive select()");
            else {
                to_write -= w;
            }
        }
    }
}

void OutputBuffer::setError(unsigned code, const char *format, ...)
{
    // only the first error is being returned
    if (_error_message == "")
    {
        char buffer[8192];
        va_list ap;
        va_start(ap, format);
        vsnprintf(buffer, sizeof(buffer) - 1, format, ap);
        logger(LG_INFO, "error: %s", buffer);
        strcat(buffer, "\n");
        va_end(ap);
        _error_message = buffer;
        _response_code = code;
    }
}

