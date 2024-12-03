<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkSpace from '@/components/CmkSpace.vue'
import type { FormSpec, Validator } from '@/form/components/vue_formspec_components'

const props = defineProps<{
  i18nRequired: string
  space?: ('before' | 'after' | 'both') | null
  spec?: FormSpec
  show?: boolean
}>()

function required(validator: Validator): boolean {
  return (
    (validator.type === 'length_in_range' &&
      validator.min_value !== null &&
      validator.min_value > 0) ||
    (validator.type === 'number_in_range' &&
      validator.min_value !== null &&
      validator.min_value > 0)
  )
}
</script>

<template>
  <span v-if="show!! || spec?.validators?.some(required)" class="form-required">
    <CmkSpace v-if="space === 'before' || space === 'both'" :size="'small'" />({{
      props.i18nRequired
    }})<CmkSpace v-if="space === 'after' || space === 'both'" :size="'small'"
  /></span>
</template>

<style scoped>
span.form-required {
  color: var(--form-element-required-color);
}
</style>
