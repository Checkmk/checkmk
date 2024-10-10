<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
export interface DropdownOption {
  ident: string | number
  name: string
}

const props = defineProps({
  options: {
    type: Array as () => DropdownOption[],
    required: true
  },
  input_hint: {
    type: String,
    default: ''
  },
  disabled: {
    type: Boolean,
    default: false
  },
  componentId: {
    type: String,
    default: ''
  }
})

const selectedOption = defineModel<string>('selectedOption', { required: true })
</script>

<template>
  <select :id="props.componentId" v-model="selectedOption" :disabled="props.disabled">
    <option v-if="selectedOption === ''" disabled selected hidden value="">
      {{ props.input_hint }}
    </option>
    <option v-for="option in props.options" :key="option.ident" :value="option.ident">
      {{ option.name }}
    </option>
  </select>
</template>

<style scoped></style>
