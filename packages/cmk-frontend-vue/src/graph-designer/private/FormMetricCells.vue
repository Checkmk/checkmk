<!--
Copyright (C) 2024 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { computed, ref, watch } from 'vue'

import usei18n from '@/lib/i18n'
import { immediateWatch } from '@/lib/watch'

import FormValidation from '@/components/user-input/CmkInlineValidation.vue'

import FormAutocompleter from '@/form/private/FormAutocompleter/FormAutocompleter.vue'
import { type ValidationMessages } from '@/form/private/validation'

const { _t } = usei18n()

export interface Metric {
  hostName: string | null
  serviceName: string | null
  metricName: string | null
}

const props = defineProps<{
  backendValidation?: ValidationMessages
}>()

const hostName = defineModel<string | null>('hostName', { default: null })
const serviceName = defineModel<string | null>('serviceName', { default: null })
const metricName = defineModel<string | null>('metricName', { default: null })

const validationByLocation = ref<{
  host_name: string[]
  service_name: string[]
  metric_name: string[]
}>({
  host_name: [],
  service_name: [],
  metric_name: []
})

immediateWatch(
  () => props.backendValidation,
  (newValidation: ValidationMessages | undefined) => {
    validationByLocation.value = { host_name: [], service_name: [], metric_name: [] }
    if (newValidation && newValidation.length > 0) {
      newValidation.forEach((message) => {
        const location = message.location[0] as 'host_name' | 'service_name' | 'metric_name'
        validationByLocation.value[location]?.push(message.message)
      })
    }
  }
)

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
    <FormValidation :validation="validationByLocation.host_name" />
    <FormAutocompleter
      v-model="hostName"
      :autocompleter="hostNameAutocompleter"
      :size="0"
      :placeholder="_t('Host name')"
      :has-error="validationByLocation.host_name.length > 0"
      @update:model-value="validationByLocation.host_name = []"
    />
  </td>
  <td>
    <FormValidation :validation="validationByLocation.service_name" />
    <FormAutocompleter
      v-model="serviceName"
      :autocompleter="serviceNameAutocompleter"
      :size="0"
      :placeholder="_t('Service name')"
      :has-error="validationByLocation.service_name.length > 0"
      @update:model-value="validationByLocation.service_name = []"
    />
  </td>
  <td>
    <FormValidation :validation="validationByLocation.metric_name" />
    <FormAutocompleter
      v-model="metricName"
      :autocompleter="metricNameAutocompleter"
      :size="0"
      :placeholder="_t('Metric name')"
      :has-error="validationByLocation.metric_name.length > 0"
      @update:model-value="validationByLocation.metric_name = []"
    />
  </td>
</template>
