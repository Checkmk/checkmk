/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import { type Ref, reactive, ref } from 'vue'

import type { MapConfigApi, SignedMap } from '@/maps/api/mapConfig'
import type { MapStatesApi } from '@/maps/api/mapStates'
import type {
  CfgImport,
  FolderTreeView,
  MapBulkDeleteResult,
  MapBulkEditResult,
  MapConfig,
  MapEnvelope,
  MapRead,
  RenderMode,
  ServiceLayout
} from '@/maps/types/api'
import { newMapView } from '@/maps/utils/model'

/** Edits are optimistic and coalesced; this is how long a burst is collected. */
const SAVE_DEBOUNCE_MS = 400

/** The view fields an operator can change from the map itself. */
export interface ViewChoices {
  problems_only?: boolean
  service_layout?: ServiceLayout
  default_view?: FolderTreeView['default_view']
}

/**
 * The maps themselves: the list, the one that is open, and everything that
 * writes one.
 *
 * The editor mutates the open map in place and asks for a save; the whole map is
 * then persisted, debounced, through the REST API. Per-operation writes would
 * turn a drag across the canvas into a burst of requests.
 */
export class MapService {
  public readonly maps: Ref<MapRead[]> = ref([])
  public readonly currentMap: Ref<MapConfig | null> = ref(null)
  /**
   * The GUI-signed blob for the open map, handed to the daemon at register time.
   * Kept apart from ``currentMap`` because that one carries client-only extras
   * (merged worldmap auto-objects) which must not be in the bytes the daemon
   * verifies — it inflates those itself.
   */
  public readonly currentMapSig: Ref<{ config_b64: string; sig: string } | null> = ref(null)
  public readonly loading: Ref<boolean> = ref(false)
  public readonly saving: Ref<boolean> = ref(false)
  public readonly error: Ref<string | null> = ref(null)
  /** Bumped per map to make a changed background image reload. */
  public readonly bgRefreshTicks: Ref<Record<string, number>> = ref({})
  /**
   * What an operator chose to look at on a map that takes no writes, by map
   * name. Read-only means "this map is not rewritten", not "the operator may not
   * choose what to look at", so the choice is kept here instead -- for as long
   * as the app lives, and no longer: a reconnected custom element starts over.
   */
  public readonly sessionViewChoices: Map<string, ViewChoices> = reactive(new Map())

  private saveTimer: ReturnType<typeof setTimeout> | null = null
  /**
   * The map captured when the debounce was armed. Persisting this reference
   * rather than whatever is open when it fires means a map switch inside the
   * debounce window still saves the edited map — the editor mutates this same
   * object, so it stays current.
   */
  private pendingSaveMap: MapConfig | null = null
  /**
   * Monotonic, so overlapping loads cannot let a slower earlier one publish after
   * a rapid switch. The view is reused across maps rather than remounted.
   */
  private fetchSeq = 0

  public constructor(
    private readonly api: Pick<
      MapConfigApi,
      'create' | 'update' | 'list' | 'get' | 'delete' | 'parseCfg'
    >,
    private readonly statesApi: Pick<MapStatesApi, 'fetchAutoObjects'>
  ) {}

  public bumpBgRefreshTick(name: string): void {
    this.bgRefreshTicks.value[name] = Date.now()
  }

  public async fetchMaps(): Promise<void> {
    const { _t } = usei18n()
    this.loading.value = true
    this.error.value = null
    try {
      this.maps.value = await this.api.list()
    } catch (e: unknown) {
      this.error.value = e instanceof Error ? e.message : _t('Failed to load maps')
    } finally {
      this.loading.value = false
    }
  }

  public async fetchMap(name: string): Promise<void> {
    const { _t } = usei18n()
    const seq = ++this.fetchSeq
    this.loading.value = true
    this.error.value = null
    this.currentMap.value = null
    this.currentMapSig.value = null
    try {
      const signed = await this.api.get(name)
      if (seq !== this.fetchSeq) {
        return
      }
      const cfg = signed.config
      // Stamping the resolved titles here rather than looking them up where a
      // link is rendered gets the caption right in the first paint, and gets it
      // right everywhere at once (caption, hover, context menu, aria label).
      cfg.objects = cfg.objects.map((object) =>
        object.type === 'map' && object.map_name
          ? { ...object, map_title: signed.map_link_titles[object.map_name] ?? null }
          : object
      )
      // A worldmap with an auto source merges transient hosts on top of the
      // persisted set. It happens here rather than in the editor so the canvas,
      // the drawer and the stream all see one object list.
      const worldmap = cfg.view?.type === 'worldmap' ? cfg.view : null
      if (worldmap?.auto_source) {
        try {
          const auto = await this.statesApi.fetchAutoObjects(name)
          if (seq !== this.fetchSeq) {
            return
          }
          cfg.objects = [...cfg.objects, ...auto]
        } catch {
          // An auto-source failure must not block the persisted view.
        }
      }
      this.currentMapSig.value = { config_b64: signed.config_b64, sig: signed.sig }
      this.currentMap.value = cfg
    } catch (e: unknown) {
      if (seq === this.fetchSeq) {
        this.error.value = e instanceof Error ? e.message : _t('Failed to load map')
      }
    } finally {
      if (seq === this.fetchSeq) {
        this.loading.value = false
      }
    }
  }

  /** One map's stored config, without the auto-source merge {@link fetchMap} does. */
  /**
   * The per-map pagetype capability the backend stamps on the map-list entry:
   * admin rights ride in via "edit foreign maps", not via configure/admin status.
   */
  public mayEdit(name: string): boolean {
    return this.maps.value.find((entry) => entry.name === name)?.can_edit === true
  }

  public async getMap(name: string): Promise<MapConfig> {
    return (await this.api.get(name)).config
  }

  public async getSignedMap(name: string): Promise<SignedMap> {
    return this.api.get(name)
  }

  public scheduleSave(): void {
    this.pendingSaveMap = this.currentMap.value
    if (this.saveTimer) {
      clearTimeout(this.saveTimer)
    }
    this.saveTimer = setTimeout(() => {
      this.saveTimer = null
      const map = this.pendingSaveMap
      this.pendingSaveMap = null
      if (map) {
        void this.persist(map)
      }
    }, SAVE_DEBOUNCE_MS)
  }

  /**
   * Sends what is still debounced and stops the timer. Not awaited: teardown
   * is synchronous, and the request outliving the app is the point.
   */
  public dispose(): void {
    void this.flushSave()
  }

  /** Persists at once, cancelling a pending debounce — for navigating away. */
  public async flushSave(): Promise<void> {
    if (this.saveTimer) {
      clearTimeout(this.saveTimer)
      this.saveTimer = null
    }
    const map = this.pendingSaveMap
    this.pendingSaveMap = null
    if (map) {
      await this.persist(map)
    }
  }

  public async createMap(
    name: string,
    alias: string,
    connectionId = 'live_1',
    mapType = 'static',
    iconSize?: number | null,
    renderMode: RenderMode = 'default'
  ): Promise<MapConfig> {
    const cfg: MapConfig = {
      name,
      alias,
      connection_id: connectionId,
      icon_size: iconSize ?? null,
      rotation_interval: 0,
      sort_order: 0,
      click_action: 'link',
      render_mode: renderMode,
      default_z: 1,
      version: 0,
      view: newMapView(mapType),
      objects: []
    }
    await this.api.create(cfg)
    // Appended rather than re-fetched: the list row is a projection of the
    // config we just sent.
    this.maps.value.push({
      name: cfg.name,
      alias: cfg.alias,
      background_image: cfg.background_image ?? null,
      icon_size: cfg.icon_size ?? null,
      connection_id: cfg.connection_id,
      view_type: cfg.view.type,
      view: cfg.view,
      object_count:
        cfg.objects.length +
        (cfg.view.type === 'presentation' ? (cfg.view.elements?.length ?? 0) : 0),
      rotation_interval: cfg.rotation_interval,
      sort_order: cfg.sort_order,
      click_action: cfg.click_action,
      hide_in_monitor_menu: false,
      hover_template: cfg.hover_template ?? null,
      context_template: cfg.context_template ?? null,
      render_mode: cfg.render_mode,
      // The creator owns the new map, so may edit and delete it.
      can_edit: true,
      can_delete: true
    })
    return cfg
  }

  public async deleteMap(name: string): Promise<void> {
    await this.api.delete(name)
    this.maps.value = this.maps.value.filter((m) => m.name !== name)
  }

  /**
   * Saves metadata for a map that need not be the open one — the settings dialog
   * runs against any map in the list. Loads the base, merges the changes,
   * persists the whole map and keeps the open map and the list row in step.
   */
  public async saveMapMetadata(
    name: string,
    updates: Partial<MapConfig>,
    envelope?: MapEnvelope
  ): Promise<MapConfig> {
    const base =
      this.currentMap.value?.name === name ? this.currentMap.value : await this.getMap(name)
    const merged: MapConfig = { ...base, ...updates }
    await this.api.update(merged, envelope)
    if (this.currentMap.value?.name === name) {
      this.currentMap.value = merged
    }
    const row = this.maps.value.find((m) => m.name === name)
    if (row) {
      row.alias = merged.alias
      row.connection_id = merged.connection_id
      row.icon_size = merged.icon_size ?? null
      row.rotation_interval = merged.rotation_interval
      row.click_action = merged.click_action
      row.render_mode = merged.render_mode
      row.background_image = merged.background_image ?? null
      row.background_color = merged.background_color ?? null
      row.hover_template = merged.hover_template ?? null
      row.context_template = merged.context_template ?? null
      row.view = merged.view
      row.view_type = merged.view.type
      if (envelope !== undefined) {
        row.public = envelope.public
        row.hide_in_monitor_menu = envelope.hide_in_monitor_menu
      }
    }
    return merged
  }

  /**
   * Stamps a new order onto the maps. The list endpoint sorts by ``sort_order``,
   * so this survives a reload. Saved one by one: reordering is rare and the lists
   * are small.
   */
  public async reorderMaps(order: { name: string; sort_order: number }[]): Promise<void> {
    for (const { name, sort_order: sortOrder } of order) {
      await this.saveMapMetadata(name, { sort_order: sortOrder })
    }
  }

  public async cloneMap(srcName: string, newName: string, alias?: string): Promise<void> {
    const src = await this.getMap(srcName)
    // A clone starts private, and out of the Monitor menu where its source is.
    const hidden = this.maps.value.find((m) => m.name === srcName)?.hide_in_monitor_menu
    await this.api.create(
      { ...src, name: newName, ...(alias ? { alias } : {}) },
      { public: false, hide_in_monitor_menu: hidden ?? false }
    )
    await this.fetchMaps()
  }

  /**
   * Imports a map config. Refuses an existing name unless told to overwrite, so
   * the caller can ask first.
   */
  public async importMapJson(map: MapConfig, overwrite: boolean): Promise<void> {
    if (!overwrite && this.maps.value.some((m) => m.name === map.name)) {
      throw new Error(`Map '${map.name}' already exists`)
    }
    await (overwrite ? this.api.update(map) : this.api.create(map))
    await this.fetchMaps()
  }

  public parseCfg(file: File): Promise<CfgImport> {
    return this.api.parseCfg(file)
  }

  public async bulkDeleteMaps(names: string[]): Promise<MapBulkDeleteResult> {
    const { _t } = usei18n()
    const deleted: string[] = []
    const failed: { name: string; reason: string }[] = []
    for (const name of names) {
      try {
        await this.api.delete(name)
        deleted.push(name)
      } catch (e: unknown) {
        failed.push({ name, reason: e instanceof Error ? e.message : _t('delete failed') })
      }
    }
    if (deleted.length > 0) {
      const removed = new Set(deleted)
      this.maps.value = this.maps.value.filter((m) => !removed.has(m.name))
    }
    return { deleted, failed }
  }

  public async bulkEditMaps(
    names: string[],
    updates: Partial<MapConfig>
  ): Promise<MapBulkEditResult> {
    const { _t } = usei18n()
    const updated: string[] = []
    const failed: { name: string; reason: string }[] = []
    for (const name of names) {
      try {
        await this.saveMapMetadata(name, updates)
        updated.push(name)
      } catch (e: unknown) {
        failed.push({ name, reason: e instanceof Error ? e.message : _t('edit failed') })
      }
    }
    return { updated, failed }
  }

  private async persist(map: MapConfig): Promise<void> {
    const { _t } = usei18n()
    this.saving.value = true
    try {
      // Updated in place: the server resolves own/foreign/built-in by name and
      // preserves the stored visibility when it is omitted, which is what a
      // routine autosave wants.
      await this.api.update(map)
      this.error.value = null
    } catch (e: unknown) {
      this.error.value = e instanceof Error ? e.message : _t('Failed to save map')
    } finally {
      this.saving.value = false
    }
  }
}
