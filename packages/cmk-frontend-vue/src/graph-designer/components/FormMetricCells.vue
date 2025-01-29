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

const data = defineModel<Metric>('data', {
  default: { hostName: '', serviceName: '', metricName: '' }
})

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
        context: { host: { host: data.value.hostName } }
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
          host: { host: data.value.hostName },
          service: { service: data.value.serviceName }
        }
      }
    }
  })
})
const backendValidationMetricName: ValidationMessages = []

// Clear form fields if one changes

watch(
  () => data.value.hostName,
  () => {
    data.value.serviceName = ''
    data.value.metricName = ''
  }
)

watch(
  () => data.value.serviceName,
  () => {
    data.value.metricName = ''
  }
)
</script>

<template>
  <td>
    <FormEdit
      v-model:data="data.hostName"
      :spec="specHostName"
      :backend-validation="backendValidationHostName"
    />
  </td>
  <td>
    <FormEdit
      :key="data.hostName"
      v-model:data="data.serviceName"
      :spec="specServiceName"
      :backend-validation="backendValidationServiceName"
    />
  </td>
  <td>
    <FormEdit
      :key="data.serviceName"
      v-model:data="data.metricName"
      :spec="specMetricName"
      :backend-validation="backendValidationMetricName"
    />
  </td>
</template>
