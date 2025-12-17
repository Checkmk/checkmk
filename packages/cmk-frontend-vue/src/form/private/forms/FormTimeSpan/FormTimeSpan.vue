<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { TimeSpan } from 'cmk-shared-typing/typescript/vue_formspec_components'

import CmkTimeSpan from '@/components/user-input/CmkTimeSpan/CmkTimeSpan.vue'

import { type ValidationMessages } from '@/form/private/validation'

defineProps<{
  spec: TimeSpan
  backendValidation: ValidationMessages
}>()

// TODO: this null value is only there to indicate that the checkbox in the dictionary is
// activated but no value is selected. this should not be our concern in this component
// but handled differently in the dictionary.
const data = defineModel<number | null>('data', { required: true })
</script>

<template>
  <CmkTimeSpan
    v-model:data="data"
    :label="spec.label"
    :title="spec.title"
    :input-hint="spec.input_hint"
    :displayed-magnitudes="spec.displayed_magnitudes"
    :validators="spec.validators"
    :backend-validation="backendValidation"
  />
</template>
