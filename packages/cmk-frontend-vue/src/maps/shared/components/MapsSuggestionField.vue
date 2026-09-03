<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Picking one entry out of a list the caller already fetched — a host, a service,
a group, a BI aggregation, another map, a metric.

The dropdown filters the list it was given rather than querying a backend, but
it takes the callback form regardless: that caps how many entries are rendered
at once, and it keeps showing a value the list no longer carries (a host that
was removed from the site stays visible on the object instead of silently
reading as "nothing picked").

Every editing surface in Maps is a bounded overlay -- an add panel in a corner,
a card over the canvas -- so the list is ``floating``: it is portalled out of
the box that would clip it and flips above the field when there is no room
below. In flow it would be cut off at the panel edge and run off the screen.
-->
<script setup lang="ts">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed } from 'vue'

import { type SuggestionList, localSuggestions } from '@/maps/shared/suggestions'

const props = defineProps<{
  list: SuggestionList
  /**
   * Names the field for assistive technology. The visible label the field sits
   * under, not ``placeholder``: that one is a hint ("Whole host if empty"),
   * which reads as nonsense when announced as the control's name.
   */
  label: TranslatedString
  placeholder: TranslatedString
  /** Says why the list is empty — a site with no host groups, say. */
  emptyHint?: TranslatedString | undefined
  disabled?: boolean
}>()

const model = defineModel<string>({ required: true })

const { _t } = usei18n()

// Read the entries here rather than only inside the callback, so the options
// object is rebuilt once the list arrives. CmkDropdown resolves the label of an
// already-picked value in a watcher on (value, options): a field opened while
// the list was still empty would otherwise keep showing `noElementsText`
// forever, and read as "Loading…" over a host that is in fact set.
const options = computed(() => {
  const items = props.list.items.value
  return {
    type: 'callback-filtered' as const,
    querySuggestions: localSuggestions(() => items)
  }
})

// A list still on its way must not read as an empty one.
const noElementsText = computed<TranslatedString>(() =>
  props.list.loading.value ? _t('Loading…') : (props.emptyHint ?? _t('Nothing to pick'))
)
</script>

<template>
  <div class="maps-suggestion-field">
    <CmkDropdown
      floating
      :model-value="model || null"
      :options="options"
      :input-hint="placeholder"
      :label="label"
      :no-results-hint="_t('No results found')"
      :no-elements-text="noElementsText"
      :disabled="disabled ?? false"
      width="fill"
      @update:model-value="model = $event ?? ''"
    />
    <p
      v-if="emptyHint && !list.loading.value && list.items.value.length === 0"
      class="maps-suggestion-field__hint"
    >
      {{ emptyHint }}
    </p>
  </div>
</template>

<style scoped>
.maps-suggestion-field__hint {
  margin: var(--dimension-3) 0 0;
  font-size: var(--font-size-normal);
  line-height: 1.375;
  color: var(--color-yellow-50);
}
</style>
