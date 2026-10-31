/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * The live state of one map, served by the Maps daemon.
 *
 * The daemon never stores a map: it is handed the config it should resolve and
 * keeps it in memory for as long as someone watches it. Everything here is
 * therefore about one already-registered map.
 */
import type { MapsDaemonClient } from '@/maps/api/transport'
import { daemonConfig } from '@/maps/api/wire'
import type {
  FolderHostService,
  FolderServiceSearchResult,
  FolderTreeOverride,
  MapConfig,
  MapElement,
  MapStates
} from '@/maps/types/api'

/**
 * An unsaved radar filter the settings preview applies without persisting it, so
 * the operator sees the effect of a filter before saving.
 */
export interface RadarOverride {
  filter: string
  filterValue: string
}

/** Unsaved view settings the settings preview shows the states of. */
export interface ViewPreview {
  radar: RadarOverride | null
  folder: FolderTreeOverride | null
}

function previewQuery({ radar, folder }: ViewPreview) {
  return {
    ...(radar && { radar_filter: radar.filter, radar_filter_value: radar.filterValue }),
    ...(folder && {
      ft_override: true,
      ft_root_folder: folder.rootFolder,
      ft_show_empty_folders: folder.showEmptyFolders,
      ft_only_hard_states: folder.onlyHardStates,
      ft_sites: folder.sites
    })
  }
}

export class MapStatesApi {
  public constructor(private readonly client: MapsDaemonClient) {}

  /**
   * Hands the daemon the GUI-signed map so its state and stream paths can resolve
   * it. The daemon verifies the signature and keys its shared loop by the map's
   * real owner (as the GUI names it for the user), so all viewers of a published
   * map share one poll. Answers with the map's full states, so opening a map takes
   * one round trip.
   */
  public async register(
    name: string,
    signed: { config_b64: string; sig: string },
    preview: ViewPreview
  ): Promise<MapStates> {
    return this.client.POST('/api/v1/maps/{name}/register', {
      params: { path: { name }, query: previewQuery(preview) },
      body: { config_b64: signed.config_b64, sig: signed.sig }
    })
  }

  /**
   * Registers the caller's own map with unsaved edits, for the editor preview.
   * The config is not stored yet, so the GUI cannot sign it; the daemon accepts
   * it unsigned only for a name that means the caller's own map, and keys it
   * under the caller, where it can never poison a foreign map's shared loop.
   */
  public async registerEdit(map: MapConfig, preview: ViewPreview): Promise<MapStates> {
    return this.client.POST('/api/v1/maps/{name}/register', {
      params: { path: { name: map.name }, query: previewQuery(preview) },
      body: { config: daemonConfig(map) }
    })
  }

  public async fetchStates(name: string, preview: ViewPreview): Promise<MapStates> {
    return this.client.GET('/api/v1/maps/{name}/states', {
      params: { path: { name }, query: previewQuery(preview) }
    })
  }

  /**
   * The transient hosts a worldmap with an auto source inflates on every load.
   * They carry synthetic ``auto:*`` ids and are never persisted — saving them
   * would freeze the live host set into the stored config.
   */
  public async fetchAutoObjects(name: string): Promise<MapElement[]> {
    return (await this.client.GET('/api/v1/maps/{name}/auto-objects', {
      params: { path: { name } }
    })) as unknown as MapElement[]
  }

  /**
   * One foldertree host's services, fetched when the operator expands that host.
   * Loading them eagerly is what makes a large site unusable.
   */
  public async fetchFolderHostServices(name: string, host: string): Promise<FolderHostService[]> {
    return this.client.GET('/api/v1/maps/{name}/folder-host-services', {
      params: { path: { name }, query: { host } }
    })
  }

  /**
   * Server-side service search across a foldertree map.
   *
   * A ``s:`` query has to reach hosts whose services were never lazily loaded, so
   * it goes through Livestatus. Pure host and folder searches stay client-side
   * and never call this.
   */
  public async searchFolderServices(
    name: string,
    terms: { s: string[]; h: string[]; q: string[] }
  ): Promise<FolderServiceSearchResult> {
    return this.client.GET('/api/v1/maps/{name}/folder-search', {
      params: { path: { name }, query: { s: terms.s, h: terms.h, q: terms.q } }
    })
  }
}
