<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { RadioGroupRoot } from 'reka-ui'

import type { TranslatedString } from '@/lib/i18nString'

import CmkInlineValidation from '@/components/user-input/CmkInlineValidation.vue'

defineOptions({ inheritAttrs: false })

const value = defineModel<string>({ required: false, default: '' })

interface CmkRadioGroupProps {
  label?: TranslatedString
  disabled?: boolean
  externalErrors?: string[]
}

const { label, disabled = false, externalErrors } = defineProps<CmkRadioGroupProps>()
</script>

<template>
  <div>
    <RadioGroupRoot
      v-model="value"
      v-bind="$attrs"
      class="cmk-radio-group"
      :aria-label="label"
      :disabled="disabled"
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
</style>
