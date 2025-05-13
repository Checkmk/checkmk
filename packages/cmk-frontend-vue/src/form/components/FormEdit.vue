<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { FormSpec } from 'cmk-shared-typing/typescript/vue_formspec_components'
import type { ValidationMessages } from '@/form/components/utils/validation'
import FormEditDispatcher from './FormEditDispatcher.vue'
import { dispatcherKey } from '@/form/private'
import { provide } from 'vue'
import { useErrorBoundary } from '@/components/useErrorBoundary'

defineProps<{
  spec: FormSpec
  backendValidation: ValidationMessages
}>()

const data = defineModel<unknown>('data', { required: true })

provide(dispatcherKey, FormEditDispatcher)

// eslint-disable-next-line @typescript-eslint/naming-convention
const { ErrorBoundary } = useErrorBoundary()
</script>

<template>
  <ErrorBoundary>
    <FormEditDispatcher v-model:data="data" :spec="spec" :backend-validation="backendValidation" />
  </ErrorBoundary>
</template>
