<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { BooleanChoice } from 'cmk-shared-typing/typescript/vue_formspec_components'

import { untranslated } from '@/lib/i18n'

import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'

import { type ValidationMessages, useValidation } from '@/form/private/validation'

const props = defineProps<{
  spec: BooleanChoice
  backendValidation: ValidationMessages
}>()

const data = defineModel<boolean>('data', { required: true })
const [validation, value] = useValidation<boolean>(
  data,
  props.spec.validators,
  () => props.backendValidation
)
</script>

<template>
  <CmkCheckbox
    v-model="value"
    :label="untranslated(spec.label ?? '')"
    :help="untranslated(spec.help)"
    :external-errors="validation"
  />
</template>
