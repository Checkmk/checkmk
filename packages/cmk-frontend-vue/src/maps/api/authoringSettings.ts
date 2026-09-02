/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * The site's authoring defaults (icon size, label style, default map type, …).
 *
 * They are edited in Checkmk's global settings, not in the SPA, which only reads
 * them to pre-fill what it creates.
 */
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

import type { GlobalSettings, TileSource } from '@/maps/types/api'

/** What the site answers: the authoring defaults and the geo maps' tile source. */
export interface AuthoringSettingsRead {
  settings: GlobalSettings
  tiles: TileSource
}

export class AuthoringSettingsApi {
  public async fetch(): Promise<AuthoringSettingsRead> {
    const read = unwrap(await client.GET('/domain-types/maps_settings/collections/all'))
    return { settings: read.settings, tiles: read.tiles }
  }
}
