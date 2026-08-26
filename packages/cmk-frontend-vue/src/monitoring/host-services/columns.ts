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

/**
 * Columns the user may hide that also map to API-optional fields.
 * When hidden, their field is omitted from the API request, so the endpoint
 * does not read it from livestatus either.
 */
const OPTIONAL_FIELD_COLUMNS = [
  'labels',
  'tags',
  'contacts',
  'contact_groups'
] as const satisfies readonly ServiceOptionalField[]

/**
 * The service optional fields (columns) the table currently shows,
 * to ask the API for those alone.
 */
export function visibleServiceFields(visibility: VisibilityState): ServiceOptionalField[] {
  return OPTIONAL_FIELD_COLUMNS.filter((field) => visibility[field] !== false)
}

/**
 * The columns frozen to the edges of the table once it has to scroll
 * horizontally.
 */
export function buildHostServicesColumnPinning(): ColumnPinningState {
  return { left: ['select', 'state', 'modes', 'name'], right: ['actions'] }
}

/** Picks a column filter offers before it refuses more, per the views-table design. */
const MAX_FILTER_CHOICES = 8

type ServiceModeField = 'in_downtime' | 'acknowledged' | 'notifications_enabled'

export function useHostServicesColumns(): ColumnDef<HostServiceEntry>[] {
  const { _t } = usei18n()

  const stateFilter: CheckboxListWithFlagsFilter<'state', 'is_flapping' | 'stale'> = {
    type: 'checkbox-list-with-flags',
    field: 'state',
    options: [
      { value: 'OK', title: _t('OK') },
      { value: 'WARN', title: _t('WARN') },
      { value: 'CRIT', title: _t('CRIT') },
      { value: 'UNKNOWN', title: _t('UNKNOWN') }
    ] satisfies { value: ServiceState; title: string }[],
    flags: [
      { field: 'is_flapping', title: _t('Flapping') },
      { field: 'stale', title: _t('Stale') }
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
    suggest: labelAutocompleter('service'),
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

  const modesFilter: BooleanGroupFilter<ServiceModeField> = {
    type: 'boolean-group',
    groups: [
      { field: 'in_downtime', title: _t('In downtime') },
      { field: 'acknowledged', title: _t('Acknowledged') },
      { field: 'notifications_enabled', title: _t('Notifications enabled') }
    ]
  }

  return [
    {
      id: 'select',
      header: '',
      enableSorting: false,
      enableHiding: false,
      minSize: 36,
      maxSize: 36,
      meta: { selectColumn: true, justify: 'center' }
    },
    {
      accessorKey: 'state',
      header: _t('State'),
      sortDescFirst: true,
      enableHiding: false,
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
      meta: { filter: summaryFilter }
    },
    {
      accessorKey: 'last_check',
      header: _t('Last check'),
      sortDescFirst: true,
      minSize: 120,
      maxSize: 200,
      meta: { filter: lastCheckFilter }
    },
    {
      accessorKey: 'last_state_change',
      header: _t('Last state change'),
      sortDescFirst: true,
      minSize: 120,
      maxSize: 200,
      meta: { filter: lastStateChangeFilter }
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
      accessorKey: 'perfometer',
      header: _t('Perf-O-Meter'),
      enableSorting: false,
      minSize: 168,
      maxSize: 168,
      meta: { justify: 'center' }
    },
    {
      id: 'actions',
      header: _t('Actions'),
      enableSorting: false,
      enableHiding: false,
      minSize: 75,
      maxSize: 75,
      meta: { justify: 'right' }
    }
  ]
}
