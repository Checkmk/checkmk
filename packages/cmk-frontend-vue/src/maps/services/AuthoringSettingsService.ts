/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref } from 'vue'

import type { AuthoringSettingsApi } from '@/maps/api/authoringSettings'
import type { GlobalSettings, TileSource } from '@/maps/types/api'

/**
 * The defaults a newly created map and object start from.
 *
 * Mirrors the server-side defaults so the SPA can render before the fetch
 * resolves; the fetched values replace them.
 */
export const SETTINGS_DEFAULTS: GlobalSettings = {
  icon_size: 30,
  view_type: 'icon',
  label_show: true,
  label_size: 11,
  label_color: '#ffffff',
  label_background: 'transparent',
  url_target: '_blank',
  z: 1,
  line_style: 'plain',
  default_backend_id: 'live_1',
  default_map_type: 'static',
  default_tile_url: null,
  default_render_mode: 'default',
  hover_template: null,
  context_template: null,
  map_list_view: 'cards'
}

/**
 * Read-only: the authoring defaults are edited in Checkmk's global settings
 * (Setup -> Global settings -> "Checkmk Maps"), never in the SPA.
 */
export class AuthoringSettingsService {
  public readonly settings: Ref<GlobalSettings> = ref({ ...SETTINGS_DEFAULTS })
  /**
   * Where geo maps fetch their tiles, and which servers the page policy allows.
   * Null until the site has answered: there is no sensible built-in default --
   * guessing one is what would reach openstreetmap.org from an air-gapped site.
   */
  public readonly tiles: Ref<TileSource | null> = ref(null)

  public constructor(private readonly api: Pick<AuthoringSettingsApi, 'fetch'>) {}

  /** Holds no timer, listener or stream. */
  public dispose(): void {}

  /**
   * Loads the site's defaults. A failure is not fatal — the SPA stays usable on
   * the factory defaults, which is better than refusing to render a map because a
   * default icon size could not be read.
   */
  public async load(): Promise<void> {
    try {
      const read = await this.api.fetch()
      this.settings.value = read.settings
      this.tiles.value = read.tiles
    } catch (e: unknown) {
      console.warn('[Maps] Failed to load authoring defaults, using built-in ones:', e)
    }
  }
}
