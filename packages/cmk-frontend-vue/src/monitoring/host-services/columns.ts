/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef, ColumnPinningState, VisibilityState } from '@tanstack/vue-table'
import usei18n from 'cmk-ui-library/lib/i18n'

import {
  autocompleter,
  labelAutocompleter,
  tagAutocompleter
} from '@/monitoring/shared/api/autocomplete'
import type {
  HostServiceEntry,
  ServiceOptionalField,
  ServiceState
} from '@/monitoring/shared/api/types'
import type {
  AutocompleteChoiceFilter,
  BooleanGroupFilter,
  CheckboxListWithFlagsFilter,
  DateTimeRangeFilter,
  StringInputFilter
} from '@/monitoring/shared/components/filter/types'
import { indicatorColumn } from '@/monitoring/shared/components/modeColumn'
import type { StateFlagField } from '@/monitoring/shared/components/stateColumn'
import { ACTIONS_COLUMN_ID } from '@/monitoring/shared/constants'
import { actionsColumnWidth } from '@/monitoring/shared/customActions'
import { columnId } from '@/monitoring/shared/tableState/schema'

/**
 * Columns the user may hide that also map to API-optional fields.
 * When hidden, their field is omitted from the API request, so the endpoint
 * does not read it from livestatus either.
 */
const OPTIONAL_FIELD_COLUMNS = [
  'labels',
  'tags',
  'contacts',
  'contact_groups',
  'groups'
] as const satisfies readonly ServiceOptionalField[]

/**
 * The service optional fields (columns) the table currently shows,
 * to ask the API for those alone.
 */
export function visibleServiceFields(visibility: VisibilityState): ServiceOptionalField[] {
  return OPTIONAL_FIELD_COLUMNS.filter((field) => visibility[field] !== false)
}

/**
 * Fields every row reads, whichever columns the table shows: the graphs beside its name, and its
 * custom icons, which also carry actions.
 */
const ROW_FIELDS = [
  'graphs_link',
  'custom_icons'
] as const satisfies readonly ServiceOptionalField[]

/**
 * The service optional fields the table asks the API for: those of the columns it shows, and
 * those every row reads.
 */
export function requestedServiceFields(visibility: VisibilityState): ServiceOptionalField[] {
  return [...visibleServiceFields(visibility), ...ROW_FIELDS]
}

export interface HostServicesColumnOptions {
  /**
   * Whether to offer the row-selection column. Only a user who may run a command on the
   * selection gets it - without one, ticking a row would lead nowhere.
   */
  includeSelect: boolean
  inlineActions?: number
  /** Whether to show the Indicator column by default; set when any service has custom icons. */
  showIndicators?: boolean
}

/**
 * The columns frozen to the edges of the table once it has to scroll
 * horizontally.
 */
export function buildHostServicesColumnPinning({
  includeSelect
}: HostServicesColumnOptions): ColumnPinningState {
  return {
    left: [...(includeSelect ? ['select'] : []), 'state', 'name'],
    right: [ACTIONS_COLUMN_ID]
  }
}

/** Picks a column filter offers before it refuses more, per the views-table design. */
const MAX_FILTER_CHOICES = 8

type ServiceModeField =
  | 'notifications_enabled'
  | 'active_checks_disabled'
  | 'passive_checks_disabled'
  | 'in_notification_period'
  | 'in_service_period'
  | 'in_check_period'
  | 'check_crashed'

export function useHostServicesColumns<Row extends HostServiceEntry = HostServiceEntry>({
  includeSelect,
  inlineActions = 0,
  showIndicators = false
}: HostServicesColumnOptions): ColumnDef<Row>[] {
  const { _t } = usei18n()

  const actionsWidth = actionsColumnWidth(inlineActions)

  const stateFilter: CheckboxListWithFlagsFilter<'state', StateFlagField> = {
    type: 'checkbox-list-with-flags',
    field: 'state',
    options: [
      { value: 'OK', title: _t('OK') },
      { value: 'WARN', title: _t('WARN') },
      { value: 'CRIT', title: _t('CRIT') },
      { value: 'UNKNOWN', title: _t('UNKNOWN') },
      { value: 'PENDING', title: _t('PENDING') }
    ] satisfies { value: ServiceState; title: string }[],
    // Same order as the icons beside the state tag, see STATE_MODE_IDS.
    flags: [
      { field: 'stale', title: _t('Stale') },
      { field: 'is_flapping', title: _t('Flapping') },
      { field: 'acknowledged', title: _t('Acknowledged') },
      { field: 'in_downtime', title: _t('In downtime') },
      { field: 'has_comments', title: _t('Has comments') }
    ]
  }

  const nameFilter: StringInputFilter<'name'> = {
    type: 'string-input',
    field: 'name'
  }

  const summaryFilter: StringInputFilter<'summary'> = {
    type: 'string-input',
    field: 'summary'
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
    op: 'all_of',
    suggest: labelAutocompleter('service'),
    keyValue: true,
    wildcardOption: true,
    maxSelected: MAX_FILTER_CHOICES
  }

  const tagsFilter: AutocompleteChoiceFilter<'tags'> = {
    type: 'autocomplete-choice',
    field: 'tags',
    op: 'all_of',
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
    op: 'one_of',
    suggest: autocompleter('allgroups', { group_type: 'contact' }),
    wildcardOption: true,
    maxSelected: MAX_FILTER_CHOICES
  }

  const serviceGroupsFilter: AutocompleteChoiceFilter<'groups'> = {
    type: 'autocomplete-choice',
    field: 'groups',
    op: 'one_of',
    suggest: autocompleter('allgroups', { group_type: 'service' }),
    wildcardOption: true,
    maxSelected: MAX_FILTER_CHOICES
  }

  const modesFilter: BooleanGroupFilter<ServiceModeField> = {
    type: 'boolean-group',
    combineLabel: _t('Combine selections with'),
    groups: [
      { field: 'notifications_enabled', title: _t('Notifications disabled'), negated: true },
      { field: 'active_checks_disabled', title: _t('Active checks disabled') },
      { field: 'passive_checks_disabled', title: _t('Passive checks disabled') },
      {
        field: 'in_notification_period',
        title: _t('Out of notification period'),
        negated: true
      },
      { field: 'in_service_period', title: _t('Out of service period'), negated: true },
      { field: 'in_check_period', title: _t('Out of check period'), negated: true },
      { field: 'check_crashed', title: _t('Check crashed') }
    ]
  }

  return [
    ...(includeSelect
      ? [
          {
            id: 'select',
            header: '',
            enableSorting: false,
            enableHiding: false,
            minSize: 36,
            maxSize: 36,
            meta: { selectColumn: true, justify: 'center' }
          } satisfies ColumnDef<Row>
        ]
      : []),
    {
      accessorKey: 'state',
      header: _t('State'),
      sortDescFirst: true,
      enableHiding: false,
      meta: { filter: stateFilter }
    },
    {
      accessorKey: 'name',
      header: _t('Service'),
      sortDescFirst: false,
      enableHiding: false,
      minSize: 150,
      maxSize: 350,
      meta: { filter: nameFilter }
    },
    {
      accessorKey: 'summary',
      header: _t('Summary'),
      sortDescFirst: false,
      minSize: 200,
      // Grows faster than the service name, since extra width saves a long summary more lines.
      meta: { filter: summaryFilter, grow: 6 }
    },
    indicatorColumn<Row, ServiceModeField>(modesFilter, showIndicators),
    {
      accessorKey: 'last_state_change',
      header: _t('State age'),
      sortDescFirst: true,
      // Replaced by `timestampColumnsAsShown` where it can size by the Timestamp Format.
      minSize: 120,
      maxSize: 200,
      meta: {
        headerTitle: _t('Age of the state'),
        justify: 'right',
        filter: lastStateChangeFilter
      }
    },
    {
      accessorKey: 'last_check',
      header: _t('Check age'),
      sortDescFirst: true,
      // Replaced by `timestampColumnsAsShown` where it can size by the Timestamp Format.
      minSize: 120,
      maxSize: 200,
      meta: {
        headerTitle: _t('Age of the check'),
        justify: 'right',
        filter: lastCheckFilter
      }
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
    {
      accessorKey: 'groups',
      header: _t('Service groups'),
      enableSorting: false,
      minSize: 100,
      maxSize: 300,
      meta: { hidden: true, filter: serviceGroupsFilter }
    },
    {
      accessorKey: 'perfometer',
      header: _t('Perf-O-Meter'),
      enableSorting: false,
      minSize: 192,
      maxSize: 192,
      meta: { justify: 'center' }
    },
    {
      id: ACTIONS_COLUMN_ID,
      header: _t('Actions'),
      enableSorting: false,
      enableHiding: false,
      minSize: actionsWidth,
      maxSize: actionsWidth,
      meta: { justify: 'right' }
    }
  ]
}

export function uncapNameWithoutSummary<Row extends HostServiceEntry>(
  columns: ColumnDef<Row>[],
  visibility: VisibilityState
): ColumnDef<Row>[] {
  if (visibility['summary'] !== false) {
    return columns
  }
  return columns.map((column) => {
    if (columnId(column) !== 'name') {
      return column
    }
    const { maxSize: _cap, ...uncapped } = column
    return uncapped
  })
}
