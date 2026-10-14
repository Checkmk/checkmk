/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { KeyShortcutService } from 'cmk-ui-library/lib/keyShortcuts'
import { type Ref, shallowRef } from 'vue'

import type { HostApi } from '@/monitoring/shared/api/hosts'
import type {
  HostEntry,
  HostOptionalField,
  HostRef,
  HostServiceEntry
} from '@/monitoring/shared/api/types'
import {
  MonitoringService,
  type MonitoringServiceOptions,
  type PagedResponse
} from '@/monitoring/shared/services/MonitoringService'

import type { HostServicesApi } from '../api/services'
import { visibleServiceFields } from '../columns'

export interface HostServicesServiceOptions extends MonitoringServiceOptions<HostServiceEntry> {
  /** Fields read on the host of the page on every fetch, for what its header and slide-in offer. */
  hostFields?: readonly HostOptionalField[]
}

export class HostServicesService extends MonitoringService<HostServiceEntry> {
  readonly hostEntry: Ref<HostEntry | null> = shallowRef<HostEntry | null>(null)
  private readonly hostFields: readonly HostOptionalField[]

  constructor(
    private readonly api: Pick<HostServicesApi, 'fetchServices'>,
    private readonly hostApi: Pick<HostApi, 'fetchHost'>,
    private readonly host: HostRef,
    shortCutService: KeyShortcutService,
    options: HostServicesServiceOptions = {}
  ) {
    super('host-services-service', shortCutService, options)
    this.hostFields = options.hostFields ?? []
  }

  protected async fetchBatch(signal: AbortSignal): Promise<PagedResponse<HostServiceEntry>> {
    const [response, hostEntry] = await Promise.all([
      this.api.fetchServices(
        this.host,
        {
          limit: this.requestedLimit.value,
          sort: this.sortState.value,
          searchQuery: this.appliedSearchQuery.value,
          filter: this.filterState.value,
          fields: visibleServiceFields(this.columnVisibility.value)
        },
        signal
      ),
      this.hostApi.fetchHost(
        this.host,
        signal,
        this.hostFields.length > 0 ? this.hostFields : undefined
      )
    ])
    this.hostEntry.value = hostEntry
    return { items: response.services, meta: response.meta }
  }
}
