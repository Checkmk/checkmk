<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { useId } from 'vue'

import type { TranslatedString } from '@/lib/i18nString'

interface RadioButtonProp {
  value: string
  label?: TranslatedString
  disabled?: boolean
  name?: string
}

defineProps<RadioButtonProp>()
const model = defineModel<string>({ required: true })
const id = useId()
</script>

<template>
  <input
    :id="id"
    v-model="model"
    type="radio"
    :value="value"
    :disabled="!!disabled"
    :name="name || ''"
  />
  <label v-if="label" :for="id">{{ label }}</label>
</template>
