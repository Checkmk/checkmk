<!--
Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { DcdMetricBackendFilter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { onBeforeUnmount, onMounted, ref } from 'vue'

import { type ValidationMessages } from '@/form/private/validation'

import FormMetricBackendAttributes from '@/metric-backend/FormMetricBackendAttributes.vue'

defineProps<{
  spec: DcdMetricBackendFilter
  backendValidation: ValidationMessages
}>()

const data = defineModel<DcdMetricBackendFilter>('data', { required: true })

const attributesComponent = ref<InstanceType<typeof FormMetricBackendAttributes> | null>(null)
const validation = ref<ValidationMessages>([])

function handleSubmit(event: SubmitEvent) {
  if (attributesComponent.value?.hasInvalidAttributes()) {
    event.preventDefault()
    validation.value = attributesComponent.value.getValidationMessages()
  } else {
    validation.value = []
  }
}

onMounted(() => {
  window.addEventListener('submit', handleSubmit)
})

onBeforeUnmount(() => {
  window.removeEventListener('submit', handleSubmit)
})
</script>

<template>
  <table>
    <FormMetricBackendAttributes
      ref="attributesComponent"
      v-model:resource-attributes="data.resource_attributes"
      v-model:scope-attributes="data.scope_attributes"
      v-model:data-point-attributes="data.data_point_attributes"
      v-model:backend-validation="validation"
      :strict="false"
      :disable-values-on-empty-key="true"
      :static-resource-attribute-keys="['service.name']"
      :indent="true"
      :orientation="'vertical'"
    />
  </table>
</template>

<style scoped>
table {
  border-collapse: separate;
  border-spacing: 5px;
}
</style>
