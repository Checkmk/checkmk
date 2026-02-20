<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import usei18n from '@/lib/i18n'
import useId from '@/lib/useId'

import CmkIcon from '../CmkIcon/'
import CmkInput from '../user-input/CmkInput.vue'
import type { DualListElement, SearchableListWidthVariants } from './index.ts'

interface CmkSearchableListProps {
  elements: DualListElement[]
  title: string

  countElements: number
  lengthElements: number
  width?: SearchableListWidthVariants | undefined
}

const props = defineProps<CmkSearchableListProps>()

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

const maxWidthMap: Record<SearchableListWidthVariants, number> = {
  xsmall: 17.4,
  small: 22.4,
  medium: 50,
  large: 75
}

const selectStyle = computed(() => {
  const contentBasedWidth = (props.lengthElements + 1) * 0.7
  const effectiveMaxWidth = maxWidthMap[(props.width ?? 'medium') as SearchableListWidthVariants]
  const width = Math.max(17.4, Math.min(contentBasedWidth, effectiveMaxWidth))
  return {
    height: props.countElements < 10 ? '200px' : `${Math.min(props.countElements * 15, 400)}px`,
    width: `${width}em`
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
  <div class="cmk-searchable-list__container">
    <div class="cmk-searchable-list__header">
      <div class="cmk-searchable-list__title">{{ props.title }}</div>
      <div>{{ selected.length }}/{{ items.length }} {{ _t('selected') }}</div>
    </div>

    <div class="cmk-searchable-list__search-input-wrapper">
      <CmkInput
        :id="`cmk-searchable-list-search-input-${componentId}`"
        v-model="search"
        :aria-label="`${_t('Filter')} ${props.title}`"
        :field-size="'FILL'"
      />
      <label
        :for="`cmk-searchable-list-search-input-${componentId}`"
        class="cmk-searchable-list__icon"
      >
        <CmkIcon name="search" size="small" />
      </label>
    </div>

    <div v-if="items.length > 0">
      <!-- size attr must not be 1 for multiple select fields as chrome defaults to a dropdown then
      https://developer.chrome.com/release-notes/142?hl=en#mobile_and_desktop_parity_for_select_element_rendering_modes -->
      <select
        v-model="selected"
        multiple="true"
        :size="Math.max(2, Math.min(items.length, 10))"
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

    <div v-else :style="selectStyle" class="cmk-searchable-list__no-element-in-select">
      {{ _t('No elements') }}
    </div>
  </div>
</template>

<style scoped>
.cmk-searchable-list__container {
  display: flex;
  flex-direction: column;
  max-width: v-bind(selectStyle.width);
}

.cmk-searchable-list__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.cmk-searchable-list__header .cmk-searchable-list__title {
  font-weight: bold;
}

.cmk-searchable-list__search-input-wrapper {
  position: relative;
  margin: 0;
  padding: 0;
}

.cmk-searchable-list__search-input-wrapper .cmk-searchable-list__icon {
  position: absolute;
  top: 0;
  right: 0;
  cursor: pointer;
  padding: 4px;
}

.cmk-searchable-list__container select {
  width: 100%;
  min-height: 150px;
  box-sizing: border-box;
  margin-top: 3px;
}

.cmk-searchable-list__no-element-in-select {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 150px;
  background-color: var(--default-form-element-bg-color);
  border-radius: 4px;
  user-select: none;
  margin-top: 3px;
}
</style>
