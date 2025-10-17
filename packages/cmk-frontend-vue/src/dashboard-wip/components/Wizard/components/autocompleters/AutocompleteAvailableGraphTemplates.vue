<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import FormAutocompleter from '@/form/private/FormAutocompleter.vue'

import type { HostServiceContext } from './types'

const { _t } = usei18n()

interface CmkAutocompleteServiceProps {
  hostName?: string | null
  serviceDescription?: string | null
}
const props = defineProps<CmkAutocompleteServiceProps>()

const combinedMetrics = defineModel<string | null>('combinedMetrics', { required: true })

const combinedMetricsAutocompleter = computed(() => {
  const context: HostServiceContext = {}
  if (props.hostName) {
    context.host = { host: props.hostName }
  }

  if (props.serviceDescription) {
    context.service = { service: props.serviceDescription }
  }

  const autocompleter: Autocompleter = {
    fetch_method: 'rest_autocomplete',
    data: {
      ident: 'available_graph_templates',
      params: {
        show_independent_of_context: true,
        escape_regex: false,
        strict: true,
        context
      }
    }
  }

  return autocompleter
})
</script>

<template>
  <FormAutocompleter
    v-model="combinedMetrics"
    :autocompleter="combinedMetricsAutocompleter"
    :size="0"
    :placeholder="_t('Select graph')"
  />
</template>
