<!--
Copyright (C) 2024 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import FormEdit from '@/form/components/FormEdit.vue'
import { type SpecLineType } from '@/graph-designer/type_defs'
import { type ValidationMessages } from '@/form'
import { makeSingleChoice } from '@/graph-designer/specs'

const props = defineProps<{
  spec: SpecLineType
}>()

const data = defineModel('data', { type: String, default: 'line' })
const spec = makeSingleChoice('', [
  { name: 'line', title: props.spec.line },
  { name: 'area', title: props.spec.area },
  { name: 'stack', title: props.spec.stack }
])
const backendValidation: ValidationMessages = []
</script>

<template>
  <FormEdit v-model:data="data" :spec="spec" :backend-validation="backendValidation" />
</template>
