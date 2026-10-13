<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown'
import {
  ErrorResponse,
  Response,
  type Suggestion,
  WarningResponse
} from 'cmk-ui-library/components/CmkSuggestions'
import type { CmkError } from 'cmk-ui-library/lib/error'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'

import {
  MAX_MATCHES,
  type ServiceNameSuggestions,
  suggestServiceNames
} from '@/mode-alerts/service-client'
import type { ServiceNameMatch } from '@/mode-alerts/types'

const { _t } = usei18n()

const { matchType, id, hasError } = defineProps<{
  matchType: ServiceNameMatch
  id?: string | undefined
  hasError?: boolean
}>()

const serviceName = defineModel<string | null>({ required: true })

// A regular expression is a pattern, not a name the site can offer, so whatever was typed
// is always selectable alongside the discovered names.
function typedName(query: string, names: string[]): Suggestion[] {
  if (query === '' || names.includes(query)) {
    return []
  }
  return [{ name: query, title: untranslated(query) }]
}

async function querySuggestions(
  query: string
): Promise<Response | WarningResponse | ErrorResponse> {
  let result: ServiceNameSuggestions
  try {
    result = await suggestServiceNames(matchType, query)
  } catch (error: unknown) {
    return new ErrorResponse((error as CmkError)?.message || _t('Unknown error'))
  }
  const suggestions: Suggestion[] = [
    ...typedName(query, result.names),
    ...result.names.map((name) => ({ name, title: untranslated(name) }))
  ]
  if (result.truncated) {
    return new WarningResponse(
      _t('Only the first %{count} names are shown. Keep typing to narrow them down.', {
        count: MAX_MATCHES
      }),
      suggestions
    )
  }
  return new Response(suggestions)
}
</script>

<template>
  <CmkDropdown
    v-model="serviceName"
    :component-id="id ?? null"
    :options="{ type: 'callback-filtered', querySuggestions }"
    :input-hint="_t('Select a service…')"
    :label="_t('Service name')"
    :no-results-hint="_t('No custom service matches this name')"
    :form-validation="hasError ?? false"
    width="fill"
    floating
  />
</template>
