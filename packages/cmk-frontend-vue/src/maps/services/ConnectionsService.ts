/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import { type Ref, ref } from 'vue'

import type { ConnectionsApi } from '@/maps/api/connections'
import type { ConnectionConfig } from '@/maps/types/api'

/**
 * The monitoring connections, for the picker and for displaying a map's own.
 *
 * Read-only: connections are configured in Checkmk's global settings.
 */
export class ConnectionsService {
  public readonly connections: Ref<ConnectionConfig[]> = ref([])
  public readonly loading: Ref<boolean> = ref(false)
  public readonly error: Ref<string | null> = ref(null)

  private inflight: Promise<void> | null = null

  public constructor(private readonly api: Pick<ConnectionsApi, 'list'>) {}

  /** Holds no timer, listener or stream. */
  public dispose(): void {}

  public async fetch(): Promise<void> {
    const { _t } = usei18n()
    this.loading.value = true
    this.error.value = null
    try {
      this.connections.value = await this.api.list()
    } catch (e: unknown) {
      this.error.value = e instanceof Error ? e.message : _t('Failed to load connections')
    } finally {
      this.loading.value = false
    }
  }

  /**
   * Loads the list once, shared by every surface that only needs it for display —
   * concurrent callers share one request instead of racing duplicates.
   */
  public ensureLoaded(): Promise<void> {
    if (this.connections.value.length) {
      return Promise.resolve()
    }
    this.inflight ??= this.fetch().finally(() => {
      this.inflight = null
    })
    return this.inflight
  }

  /**
   * Display name for a connection id, falling back to the raw id until the list
   * is loaded and for a connection that no longer exists.
   */
  public labelFor(id: string | null | undefined): string {
    if (!id) {
      return ''
    }
    return this.connections.value.find((c) => c.id === id)?.label || id
  }
}
