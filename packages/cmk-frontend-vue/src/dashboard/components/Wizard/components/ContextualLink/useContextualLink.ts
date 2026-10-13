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
  LinkedContent,
  VisualLocation
} from './contextualLink'

const { _t } = usei18n()

export interface CustomLinkDraft<F> {
  // Keys the row, so a removed row does not hand its picker state to the next one.
  id: number
  title: string
  target: VisualLocation | null
  filters: F[]
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
    filters: [],
    includeContext: true,
    includeTimeRange: true,
    showFilterForm: false
  }
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
          filters: link.filters.map((f) => f.filter_id as F),
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
        if (customLinks.value.length === 0 || customLinks.value.some(_isIncomplete)) {
          return undefined
        }
        return {
          type: 'custom',
          links: customLinks.value.map((link) => ({
            title: link.title,
            location: link.target!,
            filters: link.filters.map((filterId) => ({ filter_id: filterId })),
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
    validationErrors,
    validate,
    contextualLink
  }
}
