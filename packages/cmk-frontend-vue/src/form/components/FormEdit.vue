<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { FormSpec } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { provide } from 'vue'

import { useCmkErrorBoundary } from '@/components/CmkErrorBoundary'

import type { ValidationMessages } from '@/form/components/utils/validation'
import { dispatcherKey } from '@/form/private'

import FormEditDispatcher from './FormEditDispatcher.vue'

defineProps<{
  spec: FormSpec
  backendValidation: ValidationMessages
}>()

const data = defineModel<unknown>('data', { required: true })

provide(dispatcherKey, FormEditDispatcher)

// eslint-disable-next-line @typescript-eslint/naming-convention
const { CmkErrorBoundary } = useCmkErrorBoundary()
</script>

<template>
  <CmkErrorBoundary>
    <FormEditDispatcher v-model:data="data" :spec="spec" :backend-validation="backendValidation" />
  </CmkErrorBoundary>
</template>
