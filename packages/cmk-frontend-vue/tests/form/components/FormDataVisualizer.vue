<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import FormEdit from '@/form/components/FormEdit.vue'
import type { FormSpec } from 'cmk-shared-typing/typescript/vue_formspec_components'
import type { ValidationMessages } from '@/form/components/utils/validation'

defineProps<{
  spec: FormSpec
  backendValidation: ValidationMessages
}>()

const data = defineModel<unknown>('data', { required: true })
</script>

<template>
  <FormEdit v-model:data="data" :spec="spec" :backend-validation="backendValidation" />
  <pre data-testid="test-data">{{ JSON.stringify(data) }}</pre>
</template>
