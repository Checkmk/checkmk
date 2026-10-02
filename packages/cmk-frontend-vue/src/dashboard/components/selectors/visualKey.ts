/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Suggestion } from 'cmk-ui-library/components/CmkSuggestions'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { type ComputedRef, type Ref, type WritableComputedRef, computed } from 'vue'

const { _t } = usei18n()

/**
 * One copy of a view or dashboard: a name can exist under several owners.
 * The owner of the built-in copy is '', and null picks no copy but resolves the name.
 */
export interface VisualCopy {
  name: string
  owner: string | null
}

/** The dropdown key of a copy, since a dropdown models strings. It is never parsed back. */
export function visualKey(copy: VisualCopy): string {
  return JSON.stringify([copy.name, copy.owner])
}

/** A readable title for a copy that no list offers: a gone copy, or a name without owner. */
export function describeVisualCopy({ name, owner }: VisualCopy): TranslatedString {
  if (owner === null) {
    return _t('%{name} (resolved by name)', { name })
  }
  return untranslated(owner === '' ? name : `${name} (${owner})`)
}

/** A copy offered in a dropdown, with its title there. */
export interface CopyOption {
  copy: VisualCopy
  title: TranslatedString
}

/**
 * Dropdown suggestions and model for `selected`, which holds the picked copy itself. A stored
 * copy that no list offers is appended, so it keeps a readable label.
 */
export function useCopyOptions(
  selected: Ref<VisualCopy | null>,
  offered: () => CopyOption[]
): { suggestions: ComputedRef<Suggestion[]>; key: WritableComputedRef<string | null> } {
  const options = computed(() => {
    const listed = offered()
    const current = selected.value
    if (current !== null && !listed.some(({ copy }) => visualKey(copy) === visualKey(current))) {
      return [...listed, { copy: current, title: describeVisualCopy(current) }]
    }
    return listed
  })
  const suggestions = computed<Suggestion[]>(() =>
    options.value.map(({ copy, title }) => ({ name: visualKey(copy), title }))
  )
  const key = computed<string | null>({
    get: () => (selected.value === null ? null : visualKey(selected.value)),
    set: (picked) => {
      selected.value = options.value.find(({ copy }) => visualKey(copy) === picked)?.copy ?? null
    }
  })
  return { suggestions, key }
}
