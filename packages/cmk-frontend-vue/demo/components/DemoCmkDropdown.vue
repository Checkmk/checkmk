<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import CmkDropdown from '@/components/CmkDropdown'
import CmkDropdownButton from '@/components/CmkDropdown/CmkDropdownButton.vue'
import { ErrorResponse, Response } from '@/components/CmkSuggestions'

defineProps<{ screenshotMode: boolean }>()

const defaultSelected1 = ref<string>('init')
const defaultSelected2 = ref<string>('init')
const defaultEmpty1 = ref<string | null>(null)
const defaultEmpty2 = ref<string | null>(null)
const defaultEmpty3 = ref<string | null>(null)
const defaultEmpty4 = ref<string | null>(null)
const defaultEmpty5 = ref<string | null>(null)
const defaultEmpty6 = ref<string | null>(null)
const defaultEmpty7 = ref<string | null>(null)
const defaultEmpty8 = ref<string | null>(null)
const errorCase = ref<string | null>('invalid_backend_value')
const callCount = ref<number>(0)

// Interactive width test
const longValues = [
  {
    name: '0',
    title: 'short'
  },
  {
    name: '1',
    title: 'regular value'
  },
  {
    name: '2',
    title: 'some long value that might need truncation'
  },
  {
    name: '3',
    title: 'a very very long value that will definitely need truncation in most cases'
  },
  {
    name: '4',
    title:
      'let us be honest here this is an extremely long value that is only here to test the truncation capabilities of our CmkDropdown component'
  }
]
const truncateDivWidth = ref<number>(400)
const isResizing = ref<boolean>(false)

const startResize = (e: MouseEvent) => {
  isResizing.value = true
  const startX = e.clientX
  const startWidth = truncateDivWidth.value

  const onMouseMove = (e: MouseEvent) => {
    const delta = e.clientX - startX
    truncateDivWidth.value = Math.max(100, startWidth + delta)
  }

  const onMouseUp = () => {
    isResizing.value = false
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseup', onMouseUp)
  }

  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
}
</script>

<template>
  <h2>single element, selected</h2>
  <CmkDropdown
    v-model:selected-option="defaultSelected2"
    :options="{ type: 'fixed', suggestions: [{ name: 'init', title: 'single element' }] }"
    input-hint="some input hint"
    no-results-hint="no results hint"
    label="some label"
    required
  />
  <h2>Labeled dropdown</h2>
  <label for="labeled-dropdown">some label</label>
  <CmkDropdown
    v-model:selected-option="defaultEmpty1"
    :options="{
      type: 'fixed',
      suggestions: [
        { name: '1', title: 'one' },
        { name: '2', title: 'two' }
      ]
    }"
    component-id="labeled-dropdown"
    input-hint="some input hint"
    no-results-hint="no results hint"
    label="some label"
    required
  />
  <h2>two elements, selected</h2>
  <CmkDropdown
    v-model:selected-option="defaultSelected1"
    :options="{
      type: 'fixed',
      suggestions: [
        { name: '0', title: 'zero' },
        { name: 'init', title: 'selected by default' },
        { name: '2', title: 'two' }
      ]
    }"
    input-hint="some input hint"
    no-results-hint="no results hint"
    label="some label"
    required
  />
  <h2>two elements, empty selection</h2>
  <CmkDropdown
    v-model:selected-option="defaultEmpty2"
    :options="{
      type: 'fixed',
      suggestions: [
        { name: '1', title: 'one' },
        { name: '2', title: 'two' }
      ]
    }"
    input-hint="some input hint"
    no-results-hint="no results hint"
    label="some label"
  />
  <h2>two elements, empty selection, disabled</h2>
  <CmkDropdown
    v-model:selected-option="defaultEmpty3"
    :disabled="true"
    :options="{
      type: 'fixed',
      suggestions: [
        { name: '1', title: 'one' },
        { name: '2', title: 'two' }
      ]
    }"
    input-hint="some input hint"
    no-results-hint="no results hint"
    label="some label"
  />
  <h2>no elements, empty selection</h2>
  <CmkDropdown
    v-model:selected-option="defaultEmpty4"
    :options="{ type: 'filtered', suggestions: [] }"
    input-hint="some input hint"
    no-results-hint="no results hint"
    label="some label"
    required
  />
  <h2>many elements, filtered, empty selection</h2>
  <CmkDropdown
    v-model:selected-option="defaultEmpty5"
    :options="{
      type: 'filtered',
      suggestions: [
        ...Array(20)
          .fill(0)
          .map((_, i) => `number: ${i}`)
          .map((s) => ({ name: s, title: s }))
      ]
    }"
    input-hint="long dropdown"
    no-results-hint="no results hint"
    label="some label"
    required
  />
  <h2>callback, filtered, empty selection</h2>
  <CmkDropdown
    v-model:selected-option="defaultEmpty6"
    :options="{
      type: 'callback-filtered',
      querySuggestions: async (query) => {
        let pool = [
          { name: 'one', title: 'one' },
          { name: 'two', title: 'two' },
          { name: 'three', title: 'three' },
          { name: 'four', title: 'four' }
        ]
        pool = pool.filter((e) => e.name.includes(query))

        const directHit = pool.filter((e) => e.name === query).length === 1

        if (query !== '' && !directHit) {
          pool.splice(0, 0, { name: query, title: query })
        }
        return new Response(pool)
      }
    }"
    input-hint="long dropdown"
    no-results-hint="no results hint"
    label="some label"
    required
  />
  <h2>Queried dropdown with unselectable</h2>
  <CmkDropdown
    v-model:selected-option="defaultEmpty7"
    :options="{
      type: 'callback-filtered',
      querySuggestions: async (v) => {
        return new Response(
          [
            { name: 'one', title: 'one' },
            { name: null, title: 'unselectable' },
            { name: 'three', title: 'three' },
            { name: 'four', title: 'four' }
          ].filter((s) => s.title.includes(v))
        )
      }
    }"
    input-hint="long dropdown"
    no-results-hint="no results hint"
    label="some label"
    required
  />
  <h2>Queried dropdown with unselectable as first element</h2>
  <CmkDropdown
    v-model:selected-option="defaultEmpty3"
    :options="{
      type: 'callback-filtered',
      querySuggestions: async (v) => {
        return new Response(
          [
            { name: null, title: 'unselectable' },
            { name: 'two', title: 'two' },
            { name: 'three', title: 'three' },
            { name: 'four', title: 'four' }
          ].filter((s) => s.title.includes(v))
        )
      }
    }"
    input-hint="long dropdown"
    no-results-hint="no results hint"
    label="some label"
    required
  />

  <h2>Different widths</h2>
  <div
    :style="{
      width: `${truncateDivWidth}px`,
      border: '2px solid #ccc',
      padding: '8px',
      position: 'relative',
      cursor: isResizing ? 'ew-resize' : 'default'
    }"
  >
    <CmkDropdown
      v-model:selected-option="defaultEmpty8"
      :options="{
        type: 'filtered',
        suggestions: longValues
      }"
      input-hint="long names"
      label="some label"
      required
    />
    <h2>(wide min width)</h2>
    <CmkDropdown
      v-model:selected-option="defaultEmpty8"
      :options="{
        type: 'filtered',
        suggestions: longValues
      }"
      :width="'wide'"
      input-hint="long names"
      label="some label"
      required
    />
    <h2>(fill width)</h2>
    <CmkDropdown
      v-model:selected-option="defaultEmpty8"
      :options="{
        type: 'filtered',
        suggestions: longValues
      }"
      :width="'fill'"
      input-hint="long names"
      label="some label"
      required
    />
    <div
      :style="{
        position: 'absolute',
        right: 0,
        top: 0,
        width: '10px',
        height: '100%',
        cursor: 'ew-resize',
        backgroundColor: 'rgba(0, 123, 255, 0.1)',
        borderLeft: '2px solid #007bff'
      }"
      @mousedown.prevent="startResize"
    />
  </div>
  <p style="margin-top: 8px; color: #666; font-size: 14px">
    Current width: {{ truncateDivWidth }}px (drag the right edge to resize)
  </p>

  <h1>CmkDropdownButton</h1>
  <h2>button</h2>
  <CmkDropdownButton>default button</CmkDropdownButton>

  <h2>group start</h2>
  <CmkDropdown
    v-model:selected-option="defaultEmpty4"
    :options="{ type: 'filtered', suggestions: [] }"
    no-elements-text="no elements"
    label="some label"
  >
    <template #buttons-start><CmkDropdownButton group="start">start</CmkDropdownButton></template>
  </CmkDropdown>

  <h2>group end</h2>
  <CmkDropdown
    v-model:selected-option="defaultEmpty4"
    :options="{ type: 'filtered', suggestions: [] }"
    no-elements-text="no elements"
    label="some label"
  >
    <template #buttons-end><CmkDropdownButton group="end">end</CmkDropdownButton></template>
  </CmkDropdown>

  <h2>group both</h2>
  <CmkDropdown
    v-model:selected-option="defaultEmpty4"
    :options="{ type: 'filtered', suggestions: [] }"
    no-elements-text="no elements"
    label="some label"
  >
    <template #buttons-start><CmkDropdownButton group="start">start</CmkDropdownButton></template>
    <template #buttons-end><CmkDropdownButton group="end">end</CmkDropdownButton></template>
  </CmkDropdown>

  <h1>Error Handling for Callback-Filtered Dropdowns</h1>
  <h2>Graceful error handling with recovery</h2>
  <CmkDropdown
    v-model:selected-option="errorCase"
    :options="{
      type: 'callback-filtered',
      querySuggestions: async () => {
        callCount++
        if (callCount <= 2) {
          return new ErrorResponse('Backend error: Failed to load suggestions')
        }
        return new Response([
          { name: 'valid1', title: 'Valid Option 1' },
          { name: 'valid2', title: 'Valid Option 2' },
          { name: 'valid3', title: 'Valid Option 3' }
        ])
      }
    }"
    input-hint="Select an option"
    no-results-hint="no results"
    label="Dropdown with error recovery"
  >
    <template #buttons-start>
      <CmkDropdownButton :group="'start'">start</CmkDropdownButton>
    </template>
    <template #buttons-end>
      <CmkDropdownButton :group="'end'">end</CmkDropdownButton>
    </template>
  </CmkDropdown>
</template>

<style scoped>
h1 {
  margin-top: 2rem;
}
</style>
