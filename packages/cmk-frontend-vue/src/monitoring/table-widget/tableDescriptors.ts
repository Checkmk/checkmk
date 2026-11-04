/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef } from '@tanstack/vue-table'
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { Component } from 'vue'
import type { ComponentProps } from 'vue-component-type-helpers'

import { buildHostColumns } from '@/monitoring/all-hosts/columns'
import HostRow from '@/monitoring/all-hosts/components/HostRow.vue'
import { useAllServicesColumns } from '@/monitoring/all-services/columns'
import { uncapNameWithoutSummary } from '@/monitoring/host-services/columns'
import HostServicesRow from '@/monitoring/host-services/components/HostServicesRow.vue'
import type { HostEntry, ServiceEntry } from '@/monitoring/shared/api/types'
import {
  type RowCommand,
  performRowCommand
} from '@/monitoring/shared/components/action/rowCommand'
import type { ActionOutcome } from '@/monitoring/shared/components/action/types'
import { hostRefOfService, serviceCommand } from '@/monitoring/shared/objectRefs'
import { columnId } from '@/monitoring/shared/tableState/schema'
import { useHostActions } from '@/monitoring/shared/useHostActions'
import { useServiceActions } from '@/monitoring/shared/useServiceActions'

export type MonitoringTableName = components['schemas']['MonitoringTableContent']['table']

export interface MonitoringTableRows {
  hosts: HostEntry
  services: ServiceEntry
}

/** What the backend offers the reader to do with the rows of a table. */
export type MonitoringTableActionOffer = Pick<
  components['schemas']['MonitoringTable'],
  'actions' | 'links'
>

/** How the rows of a table get their actions, and what a command picked in a row acts on. */
export interface MonitoringTableRowActions<T, Target> {
  /** The props that hand a row its action buttons and its action menu. */
  rowProps(row: T): object
  /**
   * Run the command picked in a row, and tell how it went; null for a command not run. The signal
   * aborts once no one waits for the outcome any more.
   */
  run(row: T, command: RowCommand<Target>, signal?: AbortSignal): Promise<ActionOutcome | null>
}

/**
 * What a command picked in a row of the row component `C` acts on, as `C` emits it. A descriptor
 * runs the command with this type, so a row that changes what it emits fails to compile there.
 */
type RowCommandTarget<C> =
  ComponentProps<C> extends { onCommand?: ((command: infer Command) => unknown) | undefined }
    ? Command extends { target: infer Target }
      ? Target
      : never
    : never

export interface MonitoringTableColumn {
  id: string
  title: string
  sortable: boolean
  shownByDefault: boolean
}

/** A table of rows `T`, whose row component emits a command picked in a row naming `Target`. */
export abstract class MonitoringTableDescriptor<T, Target = unknown> {
  abstract readonly rowComponent: Component

  /** The columns the backend offers for this table. */
  abstract readonly columnIds: readonly string[]

  /** The columns of the full page, in the order the row renders them. */
  protected abstract allColumns(): ColumnDef<T>[]

  abstract rowKey(row: T): string

  abstract truncatedHint(shown: number, matched: number): string

  /**
   * The widget builds the row actions in a computed, outside any component's setup: the actions
   * must use no lifecycle hook, watcher or inject.
   */
  abstract rowActions(offer: MonitoringTableActionOffer): MonitoringTableRowActions<T, Target>

  catalog(): MonitoringTableColumn[] {
    return this.inRowOrder(this.columnIds).map(([id, column]) => ({
      id,
      title: typeof column.header === 'string' ? column.header : id,
      sortable: column.enableSorting !== false,
      shownByDefault: !column.meta?.hidden
    }))
  }

  // The row draws its cells in a fixed order, so the headers follow it, whatever order `ids` has.
  columns(ids: readonly string[]): ColumnDef<T>[] {
    return this.inRowOrder(ids).map(([, column]) => ({
      ...column,
      enableColumnFilter: false,
      enableHiding: false
    }))
  }

  private inRowOrder(ids: readonly string[]): [string, ColumnDef<T>][] {
    const wanted = new Set(ids)
    return this.allColumns().flatMap<[string, ColumnDef<T>]>((column) => {
      const id = columnId(column)
      return id !== undefined && wanted.has(id) ? [[id, column]] : []
    })
  }
}

export class HostsTableDescriptor extends MonitoringTableDescriptor<
  HostEntry,
  RowCommandTarget<typeof HostRow>
> {
  readonly rowComponent: Component = HostRow

  readonly columnIds = [
    'state',
    'modes',
    'name',
    'alias',
    'address',
    'folder',
    'site_id',
    'last_check',
    'last_state_change',
    'labels',
    'tags',
    'contacts',
    'contact_groups',
    'num_services',
    'num_services_ok',
    'num_services_warn',
    'num_services_crit',
    'num_services_unknown',
    'num_services_pending',
    'customer'
  ]

  protected allColumns(): ColumnDef<HostEntry>[] {
    return buildHostColumns({
      includeSelect: false,
      showCustomer: true,
      sites: [],
      showRelations: false
    })
  }

  rowKey(row: HostEntry): string {
    return `${row.site_id}:${row.name}`
  }

  rowActions(
    offer: MonitoringTableActionOffer
  ): MonitoringTableRowActions<HostEntry, RowCommandTarget<typeof HostRow>> {
    const { rowActions, loadActionMenu, registry } = useHostActions({
      actions: offer.actions,
      row_actions: offer.links
    })
    return {
      rowProps: () =>
        ({ rowActions, loadActionMenu }) satisfies Partial<ComponentProps<typeof HostRow>>,
      run: (_row, command, signal) => performRowCommand(registry, command, signal)
    }
  }

  truncatedHint(shown: number, matched: number): string {
    const { _t } = usei18n()
    return _t('Showing %{shown} of %{matched} hosts', {
      shown: String(shown),
      matched: String(matched)
    })
  }
}

export class ServicesTableDescriptor extends MonitoringTableDescriptor<
  ServiceEntry,
  RowCommandTarget<typeof HostServicesRow>
> {
  readonly rowComponent: Component = HostServicesRow

  readonly columnIds = [
    'state',
    'modes',
    'name',
    'summary',
    'host_name',
    'last_state_change',
    'last_check',
    'labels',
    'tags',
    'contacts',
    'contact_groups',
    'groups',
    'perfometer'
  ]

  protected allColumns(): ColumnDef<ServiceEntry>[] {
    return useAllServicesColumns({ sites: [], includeSelect: false })
  }

  override columns(ids: readonly string[]): ColumnDef<ServiceEntry>[] {
    return uncapNameWithoutSummary(super.columns(ids), { summary: ids.includes('summary') })
  }

  rowKey(row: ServiceEntry): string {
    return `${row.site_id}:${row.host_name}:${row.name}`
  }

  rowActions(
    offer: MonitoringTableActionOffer
  ): MonitoringTableRowActions<ServiceEntry, RowCommandTarget<typeof HostServicesRow>> {
    const { mayReschedule, loadActionMenu, registry } = useServiceActions({
      actions: offer.actions
    })
    return {
      rowProps: (row) =>
        ({
          mayReschedule,
          loadActionMenu: (service: string) => loadActionMenu(hostRefOfService(row), service)
        }) satisfies Partial<ComponentProps<typeof HostServicesRow>>,
      run: (row, command, signal) =>
        performRowCommand(registry, serviceCommand(hostRefOfService(row), command), signal)
    }
  }

  truncatedHint(shown: number, matched: number): string {
    const { _t } = usei18n()
    return _t('Showing %{shown} of %{matched} services', {
      shown: String(shown),
      matched: String(matched)
    })
  }
}
