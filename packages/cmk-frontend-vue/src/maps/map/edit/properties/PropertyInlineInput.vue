<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
One number of a PropertyInline row, with its short label in front and its unit
behind it.
-->
<script setup lang="ts">
import CmkLabel from 'cmk-ui-library/components/CmkLabel.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import useId from 'cmk-ui-library/lib/useId'

defineProps<{
  label: TranslatedString
  unit?: string | undefined
  min?: string | undefined
  max?: string | undefined
  /** Room for a coordinate with decimals, which the default width cuts off. */
  wide?: boolean | undefined
}>()

const value = defineModel<number>({ required: true })

const id = useId()
</script>

<template>
  <span class="maps-property-inline-input" :class="{ 'maps-property-inline-input--wide': wide }">
    <CmkLabel :for="id">{{ label }}</CmkLabel>
    <CmkInput
      :id="id"
      v-model="value"
      type="number"
      :min="min"
      :max="max"
      v-bind="unit ? { unit } : {}"
    />
  </span>
</template>

<style scoped>
.maps-property-inline-input {
  display: inline-flex;
  align-items: center;
  gap: var(--dimension-3);
  color: var(--font-color-dimmed);
}

/* CmkInput gives every number field the same narrow width and no size to
   change it; doubled to outweigh its own rule. */
/* stylelint-disable-next-line selector-pseudo-class-no-unknown */
.maps-property-inline-input--wide.maps-property-inline-input--wide :deep(input) {
  width: 12ex;
}
</style>
