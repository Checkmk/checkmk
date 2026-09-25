<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Picking the host, service or group an object is bound to, through Checkmk's own
autocompleters: the list is searched on the server as the operator types.

A value the autocompleter no longer knows -- a host removed from the site --
stays visible under its own name instead of reading as "nothing picked" over a
binding that is still stored.

A service belongs to its host, so its field stays shut until one is picked.
Floating for the same reason as MapsSuggestionField.
-->
<script setup lang="ts">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import { Response, flattenSuggestions } from 'cmk-ui-library/components/CmkSuggestions'
import { fetchSuggestions } from 'cmk-ui-library/components/FormAutocompleter/autocompleter'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed } from 'vue'

import {
  type MonitoringObjectKind,
  monitoringObjectAutocompleter
} from '@/maps/shared/monitoringAutocompleters'

const props = defineProps<{
  kind: MonitoringObjectKind
  /** The host whose services are offered; only read for ``kind: 'service'``. */
  hostName?: string | undefined
  label: TranslatedString
  placeholder: TranslatedString
}>()

const model = defineModel<string>({ required: true })

const { _t } = usei18n()

// The dropdown resolves the label of the value it holds by querying for that
// value, so this is where a stored name the autocompleter has lost is kept.
const options = computed(() => {
  const autocompleter = monitoringObjectAutocompleter(props.kind, props.hostName)
  return {
    type: 'callback-filtered' as const,
    querySuggestions: async (query: string) => {
      const result = await fetchSuggestions(autocompleter, query)
      if (!(result instanceof Response)) {
        return result
      }
      const found = flattenSuggestions(result.choices)
      const stored = model.value
      if (stored && query === stored && !found.some((entry) => entry.name === stored)) {
        found.unshift({ name: stored, title: untranslated(stored) })
      }
      return new Response(found)
    }
  }
})

const shut = computed(() => props.kind === 'service' && !props.hostName)
</script>

<template>
  <CmkDropdown
    :model-value="model || null"
    :options="options"
    :input-hint="placeholder"
    :label="label"
    :no-results-hint="_t('No results found')"
    :disabled="shut"
    width="fill"
    floating
    @update:model-value="model = $event ?? ''"
  />
</template>
