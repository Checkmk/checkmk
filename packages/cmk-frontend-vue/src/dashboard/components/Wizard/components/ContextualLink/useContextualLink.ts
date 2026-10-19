/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { type ComputedRef, type Ref, computed, ref, watch } from 'vue'

import type { UseValidate } from '../../types'
import type {
  ConfigurableMode,
  ContextFilterIdOf,
  ContextualLinkOf,
  ContextualLinkOptions,
  FilterKeyOption,
  LinkedContent,
  VisualLocation
} from './contextualLink'

const { _t } = usei18n()

export interface FilterDraft<F> {
  id: number
  filterId: F
  // The label key, tag group or aux tag; null for a filter that takes none, or until picked.
  key: string | null
  // What key the filter takes; undefined for a filter that takes none.
  keyOption: FilterKeyOption | undefined
}

export interface CustomLinkDraft<F> {
  // Keys the row, so a removed row does not hand its picker state to the next one.
  id: number
  title: string
  target: VisualLocation | null
  // Unchecked, the link carries no filters; the rows stay, so checking it again brings them back.
  includeClickedElement: boolean
  filters: FilterDraft<F>[]
  includeContext: boolean
  includeTimeRange: boolean
  showFilterForm: boolean
}

export interface UseContextualLink<C extends LinkedContent> extends UseValidate {
  modes: ConfigurableMode[]
  filters: ContextFilterIdOf<C>[]
  singleInfos: string[]
  enabled: Ref<boolean>
  mode: Ref<ConfigurableMode>
  inheritedTarget: Ref<VisualLocation | null>
  inheritedIncludeTimeRange: Ref<boolean>
  inheritedIncludesContext: boolean
  customLinks: Ref<CustomLinkDraft<ContextFilterIdOf<C>>[]>
  addCustomLink: () => void
  removeCustomLink: (index: number) => void
  /** A method, so any widget's handler fits UseContextualLink<LinkedContent>. */
  addFilter(link: CustomLinkDraft<ContextFilterIdOf<C>>, filterId: string): void
  /** Picks another filter for the draft, which then needs its own key. */
  setFilter(filter: FilterDraft<ContextFilterIdOf<C>>, filterId: string | null): void
  validationErrors: Ref<TranslatedString[]>
  /** The configured link; undefined while it is incomplete, so the widget keeps its built-in one. */
  contextualLink: ComputedRef<ContextualLinkOf<C> | undefined>
}

let nextDraftId = 0

function newCustomLink<F>(): CustomLinkDraft<F> {
  return {
    id: nextDraftId++,
    title: '',
    target: null,
    includeClickedElement: true,
    filters: [],
    includeContext: true,
    includeTimeRange: true,
    showFilterForm: false
  }
}

function newFilter<F>(
  filterId: F,
  keyOption: FilterKeyOption | undefined,
  key: string | null = null
): FilterDraft<F> {
  return { id: nextDraftId++, filterId, key, keyOption }
}

// The key as the API stores it: trimmed, and null when nothing is left.
function trimmedKey(filter: FilterDraft<unknown>): string | null {
  const key = filter.key?.trim()
  return key === undefined || key === '' ? null : key
}

export function useContextualLink<C extends LinkedContent>(
  options: ContextualLinkOptions,
  stored: C['contextual_link'] | undefined
): UseContextualLink<C> {
  type F = ContextFilterIdOf<C>
  // Each mode keeps its own state until save, so switching back and forth loses nothing.
  const enabled = ref(stored?.type !== 'none')
  const mode = ref<ConfigurableMode>(
    stored !== undefined && stored.type !== 'none' && options.modes.includes(stored.type)
      ? stored.type
      : options.modes[0]!
  )
  const inheritedTarget = ref<VisualLocation | null>(
    stored?.type === 'inherited' ? stored.location : null
  )
  const inheritedIncludeTimeRange = ref(
    stored?.type === 'inherited' ? stored.include_time_range : true
  )
  // Not offered in the editor, so a stored link keeps them and a new one pins them.
  const inheritedHidden =
    stored?.type === 'inherited'
      ? { include_context: stored.include_context, show_filter_form: stored.show_filter_form }
      : { include_context: true, show_filter_form: false }
  const customLinks = ref<CustomLinkDraft<F>[]>(
    stored?.type === 'custom'
      ? stored.links.map((link) => ({
          ...newCustomLink<F>(),
          title: link.title,
          target: link.location,
          includeClickedElement: link.filters.length > 0,
          filters: link.filters.map((f) =>
            newFilter(f.filter_id as F, options.filter_keys[f.filter_id], 'key' in f ? f.key : null)
          ),
          includeContext: link.include_context,
          includeTimeRange: link.include_time_range,
          showFilterForm: link.show_filter_form
        }))
      : [newCustomLink<F>()]
  ) as Ref<CustomLinkDraft<F>[]>
  const validationErrors = ref<TranslatedString[]>([])

  const contextualLink = computed(() => {
    const link = _buildLink()
    return link as ContextualLinkOf<C> | undefined
  })

  function _buildLink(): ContextualLinkOf<LinkedContent> | undefined {
    if (!enabled.value) {
      return { type: 'none' }
    }
    switch (mode.value) {
      case 'default':
        return { type: 'default' }
      case 'inherited':
        if (inheritedTarget.value === null) {
          return undefined
        }
        return {
          type: 'inherited',
          location: inheritedTarget.value,
          include_context: inheritedHidden.include_context,
          include_time_range: inheritedIncludeTimeRange.value,
          show_filter_form: inheritedHidden.show_filter_form
        }
      case 'custom':
        if (
          customLinks.value.length === 0 ||
          customLinks.value.some((link) => _isIncomplete(link) || _hasFilterError(link))
        ) {
          return undefined
        }
        return {
          type: 'custom',
          links: customLinks.value.map((link) => ({
            title: link.title,
            location: link.target!,
            filters: _carriedFilters(link).map((filter) => {
              const key = trimmedKey(filter)
              return key === null
                ? { filter_id: filter.filterId }
                : { filter_id: filter.filterId, key }
            }),
            include_context: link.includeContext,
            include_time_range: link.includeTimeRange,
            show_filter_form: link.showFilterForm
          }))
        } as ContextualLinkOf<LinkedContent>
    }
  }

  function _isIncomplete(link: CustomLinkDraft<F>): boolean {
    return link.title.trim() === '' || link.target === null
  }

  function _carriedFilters(link: CustomLinkDraft<F>): FilterDraft<F>[] {
    return link.includeClickedElement ? link.filters : []
  }

  function _lacksKey(filter: FilterDraft<F>): boolean {
    return filter.keyOption !== undefined && trimmedKey(filter) === null
  }

  // A label is parsed as key:value, so a colon would end the key early.
  function _hasColonInLabelKey(filter: FilterDraft<F>): boolean {
    return filter.keyOption?.type === 'label' && (trimmedKey(filter)?.includes(':') ?? false)
  }

  function _hasDuplicate(filters: FilterDraft<F>[]): boolean {
    const pairs = new Set(
      filters.map((filter) => JSON.stringify([filter.filterId, trimmedKey(filter)]))
    )
    return pairs.size !== filters.length
  }

  // The field count of each aux tag filter carried more often than it has fields.
  function _exceededAuxTagLimits(filters: FilterDraft<F>[]): number[] {
    const counts = new Map<F, { count: number; maxCount: number }>()
    for (const { filterId, keyOption } of filters) {
      if (keyOption?.type === 'aux_tag') {
        const count = (counts.get(filterId)?.count ?? 0) + 1
        counts.set(filterId, { count, maxCount: keyOption.max_count })
      }
    }
    return [...counts.values()]
      .filter(({ count, maxCount }) => count > maxCount)
      .map(({ maxCount }) => maxCount)
  }

  function _hasFilterError(link: CustomLinkDraft<F>): boolean {
    const filters = _carriedFilters(link)
    return (
      filters.some(_lacksKey) ||
      filters.some(_hasColonInLabelKey) ||
      _hasDuplicate(filters) ||
      _exceededAuxTagLimits(filters).length > 0
    )
  }

  const validate = (): boolean => {
    const errors: TranslatedString[] = []
    if (enabled.value && mode.value === 'inherited' && inheritedTarget.value === null) {
      errors.push(_t('Select a target for the contextual link.'))
    }
    if (enabled.value && mode.value === 'custom') {
      if (customLinks.value.length === 0) {
        errors.push(_t('Add at least one contextual link.'))
      } else if (customLinks.value.some(_isIncomplete)) {
        errors.push(_t('Every contextual link needs a title and a target.'))
      }
      const carried = customLinks.value.map(_carriedFilters)
      if (carried.some((filters) => filters.some(_lacksKey))) {
        errors.push(_t('Select a key for every label, tag and auxiliary tag filter.'))
      }
      if (carried.some((filters) => filters.some(_hasColonInLabelKey))) {
        errors.push(_t('A label key must not contain a colon.'))
      }
      if (carried.some(_hasDuplicate)) {
        errors.push(_t('Add each filter only once, and a label or tag filter only once per key.'))
      }
      for (const maxCount of new Set(carried.flatMap(_exceededAuxTagLimits))) {
        errors.push(_t('A link carries at most %{count} auxiliary tags.', { count: maxCount }))
      }
    }
    validationErrors.value = errors
    return errors.length === 0
  }

  // Once an error shows, re-check on every change so it goes away as soon as it is fixed.
  watch(
    [enabled, mode, inheritedTarget, customLinks],
    () => {
      if (validationErrors.value.length > 0) {
        validate()
      }
    },
    { deep: true }
  )

  return {
    modes: options.modes,
    // The constants list the filters of this widget's own union, which is what F names.
    filters: options.filters as F[],
    singleInfos: options.single_infos,
    enabled,
    mode,
    inheritedTarget,
    inheritedIncludeTimeRange,
    inheritedIncludesContext: inheritedHidden.include_context,
    customLinks,
    addCustomLink: () => customLinks.value.push(newCustomLink<F>()),
    removeCustomLink: (index: number) => customLinks.value.splice(index, 1),
    addFilter: (link, filterId) =>
      link.filters.push(newFilter(filterId as F, options.filter_keys[filterId])),
    setFilter: (filter, filterId) => {
      if (filterId !== null && filterId !== filter.filterId) {
        filter.filterId = filterId as F
        filter.key = null
        filter.keyOption = options.filter_keys[filterId]
      }
    },
    validationErrors,
    validate,
    contextualLink
  }
}
