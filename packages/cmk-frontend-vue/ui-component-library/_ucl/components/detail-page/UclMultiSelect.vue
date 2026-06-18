<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import { untranslated } from '@/lib/i18n'

import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'

const modelValue = defineModel<string[]>({ required: true })

const { options } = defineProps<{
  options: Array<{ title: string; name: string }>
}>()

const selectAllState = computed<boolean | 'indeterminate'>(() => {
  if (options.length === 0 || !options.some((o) => modelValue.value.includes(o.name))) {
    return false
  }
  return options.every((o) => modelValue.value.includes(o.name)) ? true : 'indeterminate'
})

function toggle(name: string, checked: boolean): void {
  modelValue.value = checked
    ? options.filter((o) => o.name === name || modelValue.value.includes(o.name)).map((o) => o.name)
    : modelValue.value.filter((n) => n !== name)
}

function toggleAll(checked: boolean | 'indeterminate'): void {
  modelValue.value = checked === true ? options.map((o) => o.name) : []
}
</script>

<template>
  <div class="ucl-multi-select" role="group">
    <CmkCheckbox
      :label="untranslated('Select all')"
      :model-value="selectAllState"
      :allow-indeterminate="true"
      @update:model-value="toggleAll"
    />
    <div class="ucl-multi-select__options">
      <CmkCheckbox
        v-for="option in options"
        :key="option.name"
        :label="untranslated(option.title)"
        :model-value="modelValue.includes(option.name)"
        @update:model-value="(checked) => toggle(option.name, checked)"
      />
    </div>
  </div>
</template>

<style scoped>
.ucl-multi-select {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--dimension-3);
}

.ucl-multi-select__options {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--dimension-2) var(--dimension-6);
  padding-top: var(--dimension-3);
  border-top: 1px solid var(--ucl-elements-border-color);
  width: 100%;
}
</style>
