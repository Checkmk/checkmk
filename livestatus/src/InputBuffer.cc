// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2010             mk@mathias-kettner.de |
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

#include <sys/select.h>
#include <sys/time.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <stdint.h>

#include "InputBuffer.h"
#include "logger.h"

#define READ_TIMEOUT_USEC 200000
#define QUERY_TIMEOUT    5000000  /* complete query must be read within 2 seconds */

InputBuffer::InputBuffer(int *termination_flag)
: _termination_flag(termination_flag)
{
   _read_pointer = &_readahead_buffer[0];         // points to data not yet processed
   _write_pointer = _read_pointer;                // points to end of data in buffer
   _end_pointer = _read_pointer + IB_BUFFER_SIZE; // points ot end of buffer
}

void InputBuffer::setFd(int fd)
{ 
   _fd = fd; 
   _read_pointer = _write_pointer = _readahead_buffer; 
   _requestlines.clear();
}

// read in data enough for one complete request
// (and maybe more). If this method returns IB_REQUEST_READ
// then you can subsequently retrieve the lines of the
// request with nextLine().
int InputBuffer::readRequest()
{
   // _read_pointer points to the place in the buffer, where the
   // next valid data begins. This data ends at _write_pointer.
   // That data might have been read while reading the previous
   // request.

   // r is used to find the end of the line
   char *r = _read_pointer;

   while (true)
   {
      // Try to find end of the current line in buffer
      while (r < _write_pointer && r[0] != '\n')
	 r++; // now r is at end of data or at '\n'

      // If we cannot find the end of line in the data
      // already read, then we need to read new data from
      // the client.
      if (r == _write_pointer) 
      {
	 // Is there still space left in the buffer => read in
	 // further data into the buffer.
	 if (_write_pointer < _end_pointer) 
	 {
	    int rd = readData(); // tries to read in further data into buffer

	    // Are we at end of file? That is only an error, if we've
	    // read an incomplete line. If the last thing we read was
	    // a linefeed, then we consider the current request to
	    // be valid, if it is not empty.
	    if (rd == IB_END_OF_FILE && r == _read_pointer /* currently at beginning of a line */) 
	    {
	       if (_requestlines.empty()) {
		  return IB_END_OF_FILE; // empty request -> no request
	       }
	       else {
		  // socket has been closed but request is complete
		  return IB_REQUEST_READ;
		  // the current state is now:
		  // _read_pointer == r == _write_pointer => buffer is empty
		  // that way, if the main program tries to read the
		  // next request, it will get an IB_UNEXPECTED_END_OF_FILE
	       }
	    }
	    // if we are *not* at an end of line while reading
	    // a request, we got an invalid request.
	    else if (rd == IB_END_OF_FILE)
	       return IB_UNEXPECTED_END_OF_FILE;

	    // Other status codes
	    else if (rd == IB_SHOULD_TERMINATE || rd == IB_TIMEOUT)
	       return rd;
	 }
	 // OK. So no space is left in the buffer. But maybe at the
	 // *beginning* of the buffer is space left again. This is
	 // very probable if _write_pointer == _end_pointer. Most
	 // of the buffer's content is already processed. So we simply
	 // shift the yet unprocessed data to the very left of the buffer.
	 else if (_read_pointer > _readahead_buffer) {
	    int shift_by = _read_pointer - _readahead_buffer; // distance to beginning of buffer
	    int size     = _write_pointer - _read_pointer;    // amount of data to shift
	    memmove(_readahead_buffer, _read_pointer, size);
	    _read_pointer = _readahead_buffer;                // unread data is now at the beginning
	    _write_pointer -= shift_by;                       // write pointer shifted to the left
	    r -= shift_by;                                    // current scan position also shift left
	    // continue -> still no data in buffer, but it will
	    // be read, as now is space
	 }
	 // buffer is full, but still no end of line found => buffer is too small
	 else {
	    logger(LG_INFO, "Error: maximum length of request line exceeded");
	    return IB_LINE_TOO_LONG;
	 }
      }
      else // end of line found
      {
	 if (_read_pointer == r) { // empty line found => end of request
	    _read_pointer = r + 1;
	    // Was ist, wenn noch keine korrekte Zeile gelesen wurde?
	    if (_requestlines.size() == 0) {
	       return IB_EMPTY_REQUEST;
	    }
	    else
	       return IB_REQUEST_READ;
	 }
	 else { // non-empty line: belongs to current request
	    storeRequestLine(_read_pointer, r - _read_pointer);
	    _read_pointer = r + 1;
	    r = _read_pointer;
	 }
      }
   }
}


int InputBuffer::readData()
{
   struct timeval start;
   gettimeofday(&start, NULL);
   
   struct timeval tv;
   while (!*_termination_flag) 
   {
      struct timeval now;
      gettimeofday(&now, NULL);
      int64_t elapsed = (now.tv_sec - start.tv_sec) * 1000000;
      elapsed += now.tv_usec - start.tv_usec;
      if (elapsed >= QUERY_TIMEOUT) {
	  logger(LG_INFO, "Timeout while reading query");
	  return IB_TIMEOUT;
      }

      tv.tv_sec  = READ_TIMEOUT_USEC / 1000000;
      tv.tv_usec = READ_TIMEOUT_USEC % 1000000;

      fd_set fds;
      FD_ZERO(&fds);
      FD_SET(_fd, &fds);

      int retval = select(_fd + 1, &fds, NULL, NULL, &tv);
      if (retval > 0 && FD_ISSET(_fd, &fds)) {
	 ssize_t r = read(_fd, _write_pointer, _end_pointer - _write_pointer);
	 if (r < 0) {
	    return IB_END_OF_FILE;
	 }
	 else if (r == 0) {
	    return IB_END_OF_FILE;
	 }
	 else {
	    _write_pointer += r;
	    return IB_DATA_READ;
	 }
      }
   }
   return IB_SHOULD_TERMINATE;
}


void InputBuffer::storeRequestLine(char *line, int length)
{
   char *end = line + length;
   while (end > line && isspace(*--end)) length--;
   if (length > 0)
      _requestlines.push_back(string(line, length));
   else
      logger(LG_INFO, "Warning ignoring line containing only whitespace");
}

string InputBuffer::nextLine()
{
   string s = _requestlines.front();
   _requestlines.pop_front();
   return s;
}
