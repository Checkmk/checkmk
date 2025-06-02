/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/* eslint-disable */
/**
 * This file is auto-generated via the cmk-shared-typing package.
 * Do not edit manually.
 */

export interface ModeHost {
  form_keys: ModeHostFormKeys;
  i18n: ModeHostI18N;
}
export interface ModeHostFormKeys {
  form: string;
  host_name: string;
  ipv4_address: string;
  ipv6_address: string;
  site: string;
  ip_address_family: string;
}
export interface ModeHostI18N {
  loading: string;
  error_host_not_dns_resolvable: string;
  success_host_dns_resolvable: string;
  error_ip_not_pingable: string;
  success_ip_pingable: string;
}
