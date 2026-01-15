<!--
Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { DcdMetricBackendFilter } from 'cmk-shared-typing/typescript/vue_formspec_components'

import { type ValidationMessages } from '@/form/private/validation'

import FormMetricBackendAttributes from '@/metric-backend/FormMetricBackendAttributes.vue'

defineProps<{
  spec: DcdMetricBackendFilter
  backendValidation: ValidationMessages
}>()

const data = defineModel<DcdMetricBackendFilter>('data', { required: true })
</script>

<template>
  <table>
    <FormMetricBackendAttributes
      v-model:resource-attributes="data.resource_attributes"
      v-model:scope-attributes="data.scope_attributes"
      v-model:data-point-attributes="data.data_point_attributes"
      :strict="false"
      :disable-values-on-empty-key="true"
      :static-resource-attribute-keys="['service.name']"
    />
  </table>
</template>

<style scoped>
table {
  border-collapse: separate;
  border-spacing: 5px;
}
</style>
