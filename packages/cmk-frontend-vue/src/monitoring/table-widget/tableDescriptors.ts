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
import type { HostSlideInSubject } from '@/monitoring/shared/components/HostSlideIn.vue'
import {
  type RowCommand,
  resolveRowCommand
} from '@/monitoring/shared/components/action/rowCommand'
import type { ActionRun } from '@/monitoring/shared/components/action/run'
import { hostRefOfService, refKey, serviceCommand } from '@/monitoring/shared/objectRefs'
import type { ActionFeedbackStack } from '@/monitoring/shared/services/useActionFeedbackStack'
import { columnId } from '@/monitoring/shared/tableState/schema'
import { useHostActions } from '@/monitoring/shared/useHostActions'
import { useServiceActions } from '@/monitoring/shared/useServiceActions'

import HostsTableDetails from './HostsTableDetails.vue'
import ServicesTableDetails from './ServicesTableDetails.vue'

export type MonitoringTableName = components['schemas']['MonitoringTableContent']['table']

export interface MonitoringTableRows {
  hosts: HostEntry
  services: ServiceEntry
}

/** What the backend offers the reader to do with the rows of a table. */
export type MonitoringTableActionOffer = Pick<
  components['schemas']['MonitoringTable'],
  'actions' | 'links' | 'host_actions' | 'host_links'
>

/** The actions offered on the rows of a table, and the alerts of the page that tell how they go. */
export interface MonitoringTableActions {
  offer: MonitoringTableActionOffer
  feedback: ActionFeedbackStack
}

/** How the rows of a table get their actions, and what a command picked in a row acts on. */
export interface MonitoringTableRowActions<T, Target> {
  /** The props that hand a row its action buttons and its action menu. */
  rowProps(row: T): object
  /** The run of the command picked in a row; null for a command not to run. */
  resolve(row: T, command: RowCommand<Target>): ActionRun | null
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

/**
 * The listeners a descriptor binds to the events of the row component `C`, keyed by event name and
 * typed from `C`'s emits, so a row that renames or changes an event fails to compile there.
 */
export type RowListeners<C> = {
  [K in keyof ComponentProps<C> as K extends `on${infer Event}`
    ? Uncapitalize<Event>
    : never]?: NonNullable<ComponentProps<C>[K]>
}

export interface HostsTableSubject {
  host: HostEntry
  revealRelations: boolean
}

export type ServicesTableSubject =
  | { kind: 'service'; service: ServiceEntry; graphs: boolean }
  | { kind: 'host'; host: HostSlideInSubject }

export interface MonitoringTableColumn {
  id: string
  title: string
  sortable: boolean
  shownByDefault: boolean
}

/** A table of rows `T`, whose row component emits a command picked in a row naming `Target`. */
export abstract class MonitoringTableDescriptor<T, Target = unknown, Subject = unknown> {
  abstract readonly rowComponent: Component

  abstract readonly detailsComponent: Component

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

  abstract rowListeners(row: T, open: (subject: Subject) => void): object

  /** What a click anywhere in a row opens, as a click on its name does. */
  abstract rowSubject(row: T): Subject

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
  RowCommandTarget<typeof HostRow>,
  HostsTableSubject
> {
  readonly rowComponent: Component = HostRow

  readonly detailsComponent: Component = HostsTableDetails

  readonly columnIds = [
    'state',
    'name',
    'alias',
    'address',
    'indicator',
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
      showRelations: false,
      // A dashboard is configured by hand, so it shows the indicators unless deselected there.
      showIndicators: true
    })
  }

  rowKey(row: HostEntry): string {
    return `${row.site_id}:${row.name}`
  }

  rowActions(
    offer: MonitoringTableActionOffer
  ): MonitoringTableRowActions<HostEntry, RowCommandTarget<typeof HostRow>> {
    const { rowActions, loadActionMenu, registry } = useHostActions(offer)
    return {
      rowProps: () =>
        ({ rowActions, loadActionMenu }) satisfies Partial<ComponentProps<typeof HostRow>>,
      resolve: (_row, command) => resolveRowCommand(registry, command, refKey)
    }
  }

  rowListeners(
    _row: HostEntry,
    open: (subject: HostsTableSubject) => void
  ): RowListeners<typeof HostRow> {
    return {
      open: (host: HostEntry, revealRelations: boolean = false) => open({ host, revealRelations })
    }
  }

  rowSubject(row: HostEntry): HostsTableSubject {
    return { host: row, revealRelations: false }
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
  RowCommandTarget<typeof HostServicesRow>,
  ServicesTableSubject
> {
  readonly rowComponent: Component = HostServicesRow

  readonly detailsComponent: Component = ServicesTableDetails

  readonly columnIds = [
    'state',
    'name',
    'summary',
    'indicator',
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
    return useAllServicesColumns({ sites: [], includeSelect: false, showIndicators: true })
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
    // A row offers the links into Setup in its menu, as All services does: whether the reader may
    // open the host of its service there is asked when the menu opens, not for every row.
    const menuOptions = { includeSetupLinks: offer.links.length > 0 }
    return {
      rowProps: (row) =>
        ({
          mayReschedule,
          loadActionMenu: (service: string) =>
            loadActionMenu(hostRefOfService(row), service, menuOptions)
        }) satisfies Partial<ComponentProps<typeof HostServicesRow>>,
      resolve: (row, command) =>
        resolveRowCommand(registry, serviceCommand(hostRefOfService(row), command), refKey)
    }
  }

  rowListeners(
    row: ServiceEntry,
    open: (subject: ServicesTableSubject) => void
  ): RowListeners<typeof HostServicesRow> {
    return {
      open: () => open({ kind: 'service', service: row, graphs: false }),
      openGraphs: () => open({ kind: 'service', service: row, graphs: true }),
      openHost: (host: HostSlideInSubject) => open({ kind: 'host', host })
    }
  }

  rowSubject(row: ServiceEntry): ServicesTableSubject {
    return { kind: 'service', service: row, graphs: false }
  }

  truncatedHint(shown: number, matched: number): string {
    const { _t } = usei18n()
    return _t('Showing %{shown} of %{matched} services', {
      shown: String(shown),
      matched: String(matched)
    })
  }
}
