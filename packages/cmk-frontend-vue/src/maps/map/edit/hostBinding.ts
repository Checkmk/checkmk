/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

/** The host/service pair a draft and an object form both carry. */
interface HostServiceBinding {
  host_name: string
  service_description: string
}

/**
 * Binds to another host. A service belongs to its host, so the one picked for
 * the previous host goes with it rather than ending up on a host that may not
 * run it.
 */
export function rebindHost(binding: HostServiceBinding, hostName: string): void {
  if (binding.host_name === hostName) {
    return
  }
  binding.host_name = hostName
  binding.service_description = ''
}
