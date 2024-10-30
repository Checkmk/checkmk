<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts" generic="T extends PropertyKey">
export interface DropdownOption<T> {
  ident: T
  name: string
}

const props = defineProps({
  options: {
    type: Array as () => DropdownOption<T>[],
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

const selectedOption = defineModel<T | null>('selectedOption', { required: true })
</script>

<template>
  <select
    :id="props.componentId"
    v-model="selectedOption"
    :disabled="props.disabled"
    class="drop-down"
  >
    <option v-if="selectedOption === null" disabled selected hidden :value="null">
      {{ props.input_hint }}
    </option>
    <option v-for="option in props.options" :key="option.ident" :value="option.ident">
      {{ option.name }}
    </option>
  </select>
</template>

<style scoped>
select.drop-down {
  cursor: pointer;

  &:disabled {
    cursor: auto;

    &:hover {
      background-color: var(--default-form-element-bg-color);
    }
  }
}
</style>
