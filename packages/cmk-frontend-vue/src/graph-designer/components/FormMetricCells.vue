<!--
Copyright (C) 2024 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import FormEdit from '@/form/components/FormEdit.vue'
import { computed, watch } from 'vue'
import { makeString } from '@/graph-designer/specs'
import { type ValidationMessages } from '@/form'

export interface Metric {
  hostName: string
  serviceName: string
  metricName: string
}

const hostName = defineModel<string>('hostName', { default: '' })
const serviceName = defineModel<string>('serviceName', { default: '' })
const metricName = defineModel<string>('metricName', { default: '' })

const specHostName = makeString('', 'Host name', {
  fetch_method: 'ajax_vs_autocomplete',
  data: {
    ident: 'monitored_hostname',
    params: { strict: true }
  }
})
const backendValidationHostName: ValidationMessages = []

const specServiceName = computed(() => {
  return makeString('', 'Service name', {
    fetch_method: 'ajax_vs_autocomplete',
    data: {
      ident: 'monitored_service_description',
      params: {
        strict: true,
        context: { host: { host: hostName.value } }
      }
    }
  })
})
const backendValidationServiceName: ValidationMessages = []

const specMetricName = computed(() => {
  return makeString('', 'Metric name', {
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
  })
})
const backendValidationMetricName: ValidationMessages = []

// Clear form fields if one changes

watch(
  () => hostName.value,
  () => {
    serviceName.value = ''
    metricName.value = ''
  }
)

watch(
  () => serviceName.value,
  () => {
    metricName.value = ''
  }
)
</script>

<template>
  <td>
    <FormEdit
      v-model:data="hostName"
      :spec="specHostName"
      :backend-validation="backendValidationHostName"
    />
  </td>
  <td>
    <FormEdit
      :key="hostName"
      v-model:data="serviceName"
      :spec="specServiceName"
      :backend-validation="backendValidationServiceName"
    />
  </td>
  <td>
    <FormEdit
      :key="serviceName"
      v-model:data="metricName"
      :spec="specMetricName"
      :backend-validation="backendValidationMetricName"
    />
  </td>
</template>
