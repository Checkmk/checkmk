<!--
Copyright (C) 2024 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed, watch } from 'vue'
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import FormAutocompleter from '@/form/private/FormAutocompleter.vue'

const props = defineProps<{
  placeholder_host_name: string
  placeholder_service_name: string
  placeholder_metric_name: string
}>()

export interface Metric {
  hostName: string | null
  serviceName: string | null
  metricName: string | null
}

const hostName = defineModel<string | null>('hostName', { default: null })
const serviceName = defineModel<string | null>('serviceName', { default: null })
const metricName = defineModel<string | null>('metricName', { default: null })

const hostNameAutocompleter: Autocompleter = {
  fetch_method: 'ajax_vs_autocomplete',
  data: {
    ident: 'monitored_hostname',
    params: { strict: true }
  }
}

const serviceNameAutocompleter = computed(
  () =>
    ({
      fetch_method: 'ajax_vs_autocomplete',
      data: {
        ident: 'monitored_service_description',
        params: {
          strict: true,
          context: { host: { host: hostName.value } }
        }
      }
    }) as Autocompleter
)

const metricNameAutocompleter = computed(
  () =>
    ({
      fetch_method: 'ajax_vs_autocomplete',
      data: {
        ident: 'monitored_metrics',
        params: {
          strict: true,
          context: {
            host: { host: hostName.value },
            service: { service: serviceName.value }
          }
        }
      }
    }) as Autocompleter
)

// Clear form fields if one changes

watch(
  () => hostName.value,
  () => {
    serviceName.value = null
    metricName.value = null
  }
)

watch(
  () => serviceName.value,
  () => {
    metricName.value = null
  }
)
</script>

<template>
  <td>
    <FormAutocompleter
      v-model="hostName"
      :autocompleter="hostNameAutocompleter"
      :size="0"
      :placeholder="props.placeholder_host_name"
    />
  </td>
  <td>
    <FormAutocompleter
      v-model="serviceName"
      :autocompleter="serviceNameAutocompleter"
      :size="0"
      :placeholder="props.placeholder_service_name"
    />
  </td>
  <td>
    <FormAutocompleter
      v-model="metricName"
      :autocompleter="metricNameAutocompleter"
      :size="0"
      :placeholder="props.placeholder_metric_name"
    />
  </td>
</template>
