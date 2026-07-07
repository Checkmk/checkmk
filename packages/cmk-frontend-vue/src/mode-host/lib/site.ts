/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type ModeHostSite } from 'cmk-shared-typing/typescript/mode_host'

export function resolveSiteId(
  siteInputElement: HTMLInputElement,
  siteSelectElement: HTMLSelectElement,
  siteDefaultElement: HTMLElement,
  sites: Array<ModeHostSite>
): string {
  if (siteInputElement.checked) {
    return sites.find((site) => site.id_hash === siteSelectElement.value)?.site_id ?? ''
  }
  return siteDefaultElement.textContent?.split(' - ')[0] ?? ''
}
