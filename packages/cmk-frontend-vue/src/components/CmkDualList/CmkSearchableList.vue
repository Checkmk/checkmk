<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import usei18n from '@/lib/i18n'

import { useId } from '@/form/utils'

import CmkInput from '../user-input/CmkInput.vue'
import type { DualListElement } from './index.ts'

const props = defineProps<{
  elements: DualListElement[]
  title: string

  countElements: number
  lengthElements: number
}>()

const { _t } = usei18n()
const emit = defineEmits(['element:dblclick'])

const selected = ref<string[]>([])
const search = ref<string>('')
const componentId = useId()

const handleDoubleClick = (element: DualListElement) => {
  emit('element:dblclick', element)
}

function getSelected() {
  return selected.value
    .map((name) => props.elements.find((el) => el.name === name))
    .filter((el): el is DualListElement => !!el)
}

function clearSelection() {
  selected.value = []
}

function getVisibleItems() {
  return items.value
}

defineExpose({
  getSelected,
  clearSelection,
  getVisibleItems
})

watch(
  () => props.elements,
  () => {
    selected.value = []
  },
  { deep: true, immediate: true }
)

const selectStyle = computed(() => {
  return {
    height: props.countElements < 10 ? '200px' : `${Math.min(props.countElements * 15, 400)}px`,
    width: `${Math.max(20, Math.min(100, (props.lengthElements + 1) * 0.7))}em`,
    marginTop: '3px',
    maxWidth: '440px'
  }
})

const items = computed<DualListElement[]>(() => {
  const normalizedSearch = search.value.toLowerCase()
  if (!normalizedSearch) {
    return props.elements
  }
  return props.elements.filter((element) => element.title.toLowerCase().includes(normalizedSearch))
})

watch(
  items,
  () => {
    selected.value = []
  },
  { immediate: true }
)
</script>

<template>
  <div class="cmk-searchable-list">
    <div class="cmk-searchable-list-header">
      <div class="cmk-searchable-list-title">{{ props.title }}</div>
      <div>{{ selected.length }}/{{ items.length }} {{ _t('selected') }}</div>
    </div>

    <div class="cmk-searchable-list-search-input-wrapper">
      <CmkInput
        :id="`cmk-searchable-list-search-input-${componentId}`"
        v-model="search"
        :aria-label="`${_t('Filter')} ${props.title}`"
        style="width: 100%"
      />
      <label :for="`cmk-searchable-list-search-input-${componentId}`" class="icon">
        <img />
      </label>
    </div>

    <div v-if="items.length > 0">
      <select
        v-model="selected"
        multiple
        :size="Math.min(items.length, 10)"
        :style="selectStyle"
        :aria-label="props.title"
      >
        <option
          v-for="element in items"
          :key="element.name"
          :value="element.name"
          @dblclick="() => handleDoubleClick(element)"
        >
          {{ element.title }}
        </option>
      </select>
    </div>

    <div v-else :style="selectStyle" class="cmk-searchable-list-no-element-in-select">
      {{ _t('No elements') }}
    </div>
  </div>
</template>

<style scoped>
.cmk-searchable-list {
  display: flex;
  flex-direction: column;
}
.cmk-searchable-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.cmk-searchable-list-header .cmk-searchable-list-title {
  font-weight: bold;
}
.cmk-searchable-list-search-input-wrapper {
  position: relative;
  display: flex;
  margin: 0;
  padding: 0;
}
.cmk-searchable-list-search-input-wrapper .icon {
  position: absolute;
  top: 0;
  right: 0;
}
.cmk-searchable-list-search-input-wrapper .icon img {
  content: var(--icon-search);
  cursor: pointer;
  height: 12px;
  width: 12px;
  padding: 4px;
  border-radius: 2px;
}
.cmk-searchable-list select {
  width: 100%;
  min-height: 150px;
  box-sizing: border-box;
}
.cmk-searchable-list-no-element-in-select {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 150px;
  background-color: var(--default-form-element-bg-color);
  border-radius: 4px;
  user-select: none;
}
</style>
