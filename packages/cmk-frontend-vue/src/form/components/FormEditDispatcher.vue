<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { FormSpec } from 'cmk-shared-typing/typescript/vue_formspec_components'
import type { ValidationMessages } from '@/form/components/utils/validation'
import FormHelp from '@/form/private/FormHelp.vue'
import { getComponent } from '@/form/private/dispatch'

defineProps<{
  spec: FormSpec
  backendValidation: ValidationMessages
}>()

const data = defineModel<unknown>('data', { required: true })
</script>

<template>
  <span>
    <FormHelp :help="spec.help" />
    <component
      :is="getComponent(spec.type)"
      v-model:data="data"
      :backend-validation="backendValidation"
      :spec="spec"
    />
  </span>
</template>
