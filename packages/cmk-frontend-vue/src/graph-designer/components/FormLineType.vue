<!--
Copyright (C) 2024 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import FormEdit from '@/form/components/FormEdit.vue'
import type { SpecLineType } from '@/graph-designer/components/type_defs'
import type { ValidationMessages } from '@/form'

const props = defineProps<{
  spec: SpecLineType
}>()

const dataLineType = defineModel('dataLineType', { type: String, default: 'line' })
const specLineType = {
  type: 'single_choice',
  title: '',
  help: '',
  validators: [],
  elements: [
    { name: 'line', title: props.spec.line },
    { name: 'area', title: props.spec.area },
    { name: 'stack', title: props.spec.stack }
  ],
  frozen: false
}
const backendValidationLineType: ValidationMessages = []
</script>

<template>
  <FormEdit
    v-model:data="dataLineType"
    :spec="specLineType"
    :backend-validation="backendValidationLineType"
  />
</template>
