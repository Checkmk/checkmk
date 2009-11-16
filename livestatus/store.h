// +------------------------------------------------------------------+
// |                     _           _           _                    |
// |                  __| |_  ___ __| |__  _ __ | |__                 |
// |                 / _| ' \/ -_) _| / / | '  \| / /                 |
// |                 \__|_||_\___\__|_\_\_|_|_|_|_\_\                 |
// |                                   |___|                          |
// |              _   _   __  _         _        _ ____               |
// |             / | / | /  \| |__  ___| |_ __ _/ |__  |              |
// |             | |_| || () | '_ \/ -_)  _/ _` | | / /               |
// |             |_(_)_(_)__/|_.__/\___|\__\__,_|_|/_/                |
// |                                            check_mk 1.1.0beta17  |
// |                                                                  |
// | Copyright Mathias Kettner 2009             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
// 
// This file is part of check_mk 1.1.0beta17.
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

#ifndef store_h
#define store_h

#ifdef __cplusplus 
extern "C"
{
#endif

  void store_init();
  void store_deinit();
  void store_register_service(service *);
  void store_register_host(host *);
  void store_register_contact(contact *);
  void store_register_downtime(nebstruct_downtime_data *);
  int  store_answer_request(void *input_buffer, void *output_buffer);
  void *create_outputbuffer();
  void flush_output_buffer(void *ob, int fd, int *termination_flag);
  void delete_outputbuffer(void *);
  void *create_inputbuffer(int *termination_flag);
  void set_inputbuffer_fd(void *, int fd);
  void delete_inputbuffer(void *);
  void queue_add_connection(int cc);
  int  queue_pop_connection();
  void queue_wakeup_all();

#ifdef __cplusplus
}
#endif

#endif /* store_h */

