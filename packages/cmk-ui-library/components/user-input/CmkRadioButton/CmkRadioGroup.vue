<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkInlineValidation from 'cmk-ui-library/components/user-input/CmkInlineValidation.vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { RadioGroupRoot } from 'reka-ui'

defineOptions({ inheritAttrs: false })

const value = defineModel<string>({ required: false, default: '' })

interface CmkRadioGroupProps {
  label?: TranslatedString
  disabled?: boolean
  externalErrors?: string[]
  orientation?: 'vertical' | 'horizontal'
}

const {
  label,
  disabled = false,
  externalErrors,
  orientation = 'vertical'
} = defineProps<CmkRadioGroupProps>()
</script>

<template>
  <div>
    <RadioGroupRoot
      v-model="value"
      v-bind="$attrs"
      :class="['cmk-radio-group', { 'cmk-radio-group--horizontal': orientation === 'horizontal' }]"
      :aria-label="label"
      :disabled="disabled"
      :orientation="orientation"
    >
      <slot />
    </RadioGroupRoot>
    <CmkInlineValidation :validation="externalErrors"></CmkInlineValidation>
  </div>
</template>

<style scoped>
.cmk-radio-group {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}

.cmk-radio-group--horizontal {
  flex-direction: row;
  gap: var(--dimension-7);
}
</style>
