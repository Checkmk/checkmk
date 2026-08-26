/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef, ColumnPinningState, VisibilityState } from '@tanstack/vue-table'
import type { Site } from 'cmk-shared-typing/typescript/monitoring/all_hosts'
import usei18n from 'cmk-ui-library/lib/i18n'

import {
  autocompleter,
  labelAutocompleter,
  tagAutocompleter
} from '@/monitoring/shared/api/autocomplete'
import type { HostEntry, HostOptionalField, HostState } from '@/monitoring/shared/api/types'
import type {
  AutocompleteChoiceFilter,
  BooleanGroupFilter,
  CheckboxListFilter,
  CheckboxListWithFlagsFilter,
  DateTimeRangeFilter,
  NumericFilter,
  StringInputFilter
} from '@/monitoring/shared/components/filter/types'
import { columnId } from '@/monitoring/shared/tableState/schema'

export interface HostColumnOptions {
  /** Whether to render the row-action column, which needs permitted actions. */
  includeActions: boolean
  /**
   * Whether to offer the customer column. Only hosts monitored by an edition with multi-tenancy
   * support belong to a customer, so everywhere else the column does not exist at all.
   */
  showCustomer: boolean
  /** Configured sites the user is authorized to see, for the site column's filter options. */
  sites: readonly Site[]
}

/**
 * Columns the user may hide that also map to API-optional fields.
 * When hidden, their field is omitted from the API request.
 */
const OPTIONAL_FIELD_COLUMNS = [
  'alias',
  'address',
  'folder',
  'num_services',
  'num_services_ok',
  'num_services_warn',
  'num_services_crit',
  'num_services_unknown',
  'num_services_pending',
  'last_check',
  'last_state_change',
  'labels',
  'tags',
  'contacts',
  'contact_groups'
] as const satisfies readonly HostOptionalField[]

/**
 * Columns the user may hide whose fields are always included in every API
 * response (not declared optional) and therefore never need to be requested.
 *
 * The customer is one of them because the API derives it from the site, which every host
 * carries anyway.
 */
const ALWAYS_FETCHED_HIDEABLE_COLUMNS = ['site_id', 'customer'] as const

/** Picks a column filter offers before it refuses more, per the views-table design. */
const MAX_FILTER_CHOICES = 8

const HIDEABLE_COLUMN_IDS: ReadonlySet<string> = new Set([
  ...OPTIONAL_FIELD_COLUMNS,
  ...ALWAYS_FETCHED_HIDEABLE_COLUMNS
])

/**
 * The host optional fields (columns) the table currently shows,
 * to ask the API for those alone.
 */
export function visibleHostFields(visibility: VisibilityState): HostOptionalField[] {
  return OPTIONAL_FIELD_COLUMNS.filter((field) => visibility[field] !== false)
}

function fixUnlessHideable(column: ColumnDef<HostEntry>): ColumnDef<HostEntry> {
  const id = columnId(column)
  if (id !== undefined && HIDEABLE_COLUMN_IDS.has(id)) {
    return column
  }
  return { ...column, enableHiding: false }
}

/**
 * The columns frozen to the edges of the table once it has to scroll
 * horizontally.
 */
export function buildHostColumnPinning({
  includeActions
}: Pick<HostColumnOptions, 'includeActions'>): ColumnPinningState {
  return {
    left: ['select', 'state', 'modes', 'name'],
    ...(includeActions ? { right: ['actions'] } : {})
  }
}

/**
 * The columns of the All Hosts table.
 *
 * Which ones a user may hide follows from {@link HIDEABLE_COLUMNS}; no column
 * states it itself. Columns carrying `hidden` are off until a user picks them,
 * which defines the set shown on first use.
 */
export function buildHostColumns({
  includeActions,
  showCustomer,
  sites
}: HostColumnOptions): ColumnDef<HostEntry>[] {
  const { _t } = usei18n()

  const stateFilter: CheckboxListWithFlagsFilter<'state', 'is_flapping' | 'stale'> = {
    type: 'checkbox-list-with-flags',
    field: 'state',
    options: [
      { value: 'UP', title: _t('UP') },
      { value: 'DOWN', title: _t('DOWN') },
      { value: 'UNREACHABLE', title: _t('UNREACH') }
    ] satisfies { value: HostState; title: string }[],
    flags: [
      { field: 'is_flapping', title: _t('Flapping') },
      { field: 'stale', title: _t('Stale') }
    ]
  }

  const nameFilter: StringInputFilter<'name'> = {
    type: 'string-input',
    field: 'name'
  }

  const aliasFilter: StringInputFilter<'alias'> = {
    type: 'string-input',
    field: 'alias'
  }

  const addressFilter: StringInputFilter<'address'> = {
    type: 'string-input',
    field: 'address'
  }

  const folderFilter: StringInputFilter<'folder'> = {
    type: 'string-input',
    field: 'folder'
  }

  const siteFilter: CheckboxListFilter<'site_id'> = {
    type: 'checkbox-list',
    field: 'site_id',
    options: sites.map((site) => ({ value: site.id, title: site.alias }))
  }

  const totalServicesFilter: NumericFilter<'num_services'> = {
    type: 'numeric',
    field: 'num_services'
  }

  const okServicesFilter: NumericFilter<'num_services_ok'> = {
    type: 'numeric',
    field: 'num_services_ok'
  }

  const warnServicesFilter: NumericFilter<'num_services_warn'> = {
    type: 'numeric',
    field: 'num_services_warn'
  }

  const critServicesFilter: NumericFilter<'num_services_crit'> = {
    type: 'numeric',
    field: 'num_services_crit'
  }

  const unknownServicesFilter: NumericFilter<'num_services_unknown'> = {
    type: 'numeric',
    field: 'num_services_unknown'
  }

  const pendingServicesFilter: NumericFilter<'num_services_pending'> = {
    type: 'numeric',
    field: 'num_services_pending'
  }

  const lastCheckFilter: DateTimeRangeFilter<'last_check'> = {
    type: 'date-time-range',
    field: 'last_check'
  }

  const lastStateChangeFilter: DateTimeRangeFilter<'last_state_change'> = {
    type: 'date-time-range',
    field: 'last_state_change'
  }

  const labelsFilter: AutocompleteChoiceFilter<'labels'> = {
    type: 'autocomplete-choice',
    field: 'labels',
    suggest: labelAutocompleter('host'),
    keyValue: true,
    wildcardOption: true,
    maxSelected: MAX_FILTER_CHOICES
  }

  const tagsFilter: AutocompleteChoiceFilter<'tags'> = {
    type: 'autocomplete-choice',
    field: 'tags',
    suggest: tagAutocompleter(),
    keyValue: true,
    wildcardOption: true,
    maxSelected: MAX_FILTER_CHOICES
  }

  const contactsFilter: StringInputFilter<'contacts'> = {
    type: 'string-input',
    field: 'contacts'
  }

  const contactGroupsFilter: AutocompleteChoiceFilter<'contact_groups'> = {
    type: 'autocomplete-choice',
    field: 'contact_groups',
    suggest: autocompleter('allgroups', { group_type: 'contact' }),
    wildcardOption: true,
    maxSelected: MAX_FILTER_CHOICES
  }

  const modesFilter: BooleanGroupFilter<'in_downtime' | 'acknowledged'> = {
    type: 'boolean-group',
    groups: [
      { field: 'in_downtime', title: _t('In downtime') },
      { field: 'acknowledged', title: _t('Acknowledged') }
    ]
  }

  const columns: ColumnDef<HostEntry>[] = [
    {
      id: 'select',
      header: '',
      enableSorting: false,
      minSize: 36,
      maxSize: 36,
      meta: { selectColumn: true, justify: 'center' }
    },
    {
      accessorKey: 'state',
      header: _t('State'),
      sortDescFirst: true,
      minSize: 86,
      maxSize: 131,
      meta: { filter: stateFilter }
    },
    {
      accessorKey: 'modes',
      header: _t('Mode'),
      enableSorting: false,
      minSize: 80,
      maxSize: 80,
      meta: { justify: 'left', filter: modesFilter }
    },
    {
      accessorKey: 'name',
      header: _t('Host'),
      sortDescFirst: false,
      minSize: 150,
      meta: { filter: nameFilter }
    },
    {
      accessorKey: 'alias',
      header: _t('Host alias'),
      sortDescFirst: false,
      minSize: 100,
      maxSize: 300,
      meta: { filter: aliasFilter, hidden: true }
    },
    {
      accessorKey: 'address',
      header: _t('IP address'),
      sortDescFirst: false,
      minSize: 100,
      maxSize: 300,
      meta: { filter: addressFilter }
    },
    {
      accessorKey: 'folder',
      header: _t('Folder'),
      sortDescFirst: false,
      minSize: 100,
      maxSize: 300,
      meta: { filter: folderFilter, hidden: true }
    },
    {
      accessorKey: 'site_id',
      header: _t('Site'),
      sortDescFirst: false,
      minSize: 100,
      maxSize: 300,
      meta: { filter: siteFilter, hidden: true }
    },
    {
      accessorKey: 'num_services',
      header: _t('All services'),
      sortDescFirst: true,
      meta: {
        justify: 'right',
        filter: totalServicesFilter,
        headerTitle: _t('Total number of services')
      },
      minSize: 70,
      maxSize: 130
    },
    {
      accessorKey: 'num_services_ok',
      header: _t('OK'),
      sortDescFirst: true,
      meta: {
        justify: 'right',
        filter: okServicesFilter,
        headerTitle: _t('Number of services in OK state')
      },
      minSize: 70,
      maxSize: 70
    },
    {
      accessorKey: 'num_services_warn',
      header: _t('Wa'),
      sortDescFirst: true,
      meta: {
        justify: 'right',
        filter: warnServicesFilter,
        headerTitle: _t('Number of services in warning state')
      },
      minSize: 70,
      maxSize: 70
    },
    {
      accessorKey: 'num_services_crit',
      header: _t('Cr'),
      sortDescFirst: true,
      meta: {
        justify: 'right',
        filter: critServicesFilter,
        headerTitle: _t('Number of services in critical state')
      },
      minSize: 70,
      maxSize: 70
    },
    {
      accessorKey: 'num_services_unknown',
      header: _t('Un'),
      sortDescFirst: true,
      meta: {
        justify: 'right',
        filter: unknownServicesFilter,
        headerTitle: _t('Number of services in unknown state')
      },
      minSize: 70,
      maxSize: 70
    },
    {
      accessorKey: 'num_services_pending',
      header: _t('Pd'),
      sortDescFirst: true,
      meta: {
        justify: 'right',
        filter: pendingServicesFilter,
        headerTitle: _t('Number of services in pending state')
      },
      minSize: 70,
      maxSize: 70
    },
    {
      accessorKey: 'last_check',
      header: _t('Last check'),
      sortDescFirst: true,
      minSize: 120,
      maxSize: 200,
      meta: { hidden: true, filter: lastCheckFilter }
    },
    {
      accessorKey: 'last_state_change',
      header: _t('Last state change'),
      sortDescFirst: true,
      minSize: 120,
      maxSize: 200,
      meta: { hidden: true, filter: lastStateChangeFilter }
    },
    {
      accessorKey: 'labels',
      header: _t('Labels'),
      enableSorting: false,
      minSize: 100,
      maxSize: 400,
      meta: { hidden: true, filter: labelsFilter }
    },
    {
      accessorKey: 'tags',
      header: _t('Tags'),
      enableSorting: false,
      minSize: 100,
      maxSize: 400,
      meta: { hidden: true, filter: tagsFilter }
    },
    {
      accessorKey: 'contacts',
      header: _t('Contacts'),
      enableSorting: false,
      minSize: 100,
      maxSize: 300,
      meta: { hidden: true, filter: contactsFilter }
    },
    {
      accessorKey: 'contact_groups',
      header: _t('Contact groups'),
      enableSorting: false,
      minSize: 100,
      maxSize: 300,
      meta: { hidden: true, filter: contactGroupsFilter }
    },
    ...(showCustomer
      ? [
          {
            accessorKey: 'customer',
            header: _t('Customer'),
            enableSorting: false,
            minSize: 100,
            maxSize: 300,
            meta: { hidden: true }
          } satisfies ColumnDef<HostEntry>
        ]
      : []),
    ...(includeActions
      ? [
          {
            id: 'actions',
            header: _t('Actions'),
            enableSorting: false,
            minSize: 75,
            maxSize: 75,
            meta: { justify: 'right' }
          } satisfies ColumnDef<HostEntry>
        ]
      : [])
  ]

  return columns.map(fixUnlessHideable)
}
