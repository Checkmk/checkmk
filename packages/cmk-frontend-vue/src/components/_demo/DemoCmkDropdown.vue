<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'
import CmkDropdown from '@/components/CmkDropdown.vue'
import CmkDropdownButton from '@/components/CmkDropdownButton.vue'
import { Response } from '@/components/suggestions'

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
      querySuggestions: async (_) => {
        return new Response([
          { name: 'one', title: 'one' },
          { name: null, title: 'unselectable' },
          { name: 'three', title: 'three' },
          { name: 'four', title: 'four' }
        ])
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
      querySuggestions: async (_) => {
        return new Response([
          { name: null, title: 'unselectable' },
          { name: 'two', title: 'two' },
          { name: 'three', title: 'three' },
          { name: 'four', title: 'four' }
        ])
      }
    }"
    input-hint="long dropdown"
    no-results-hint="no results hint"
    label="some label"
    required
  />
  <h2>element names that are very very long</h2>
  <CmkDropdown
    v-model:selected-option="defaultEmpty8"
    :options="{
      type: 'filtered',
      suggestions: [
        ...Array(20)
          .fill(0)
          .map((_, i) => ({
            name: i.toString(),
            title: `some ${'very '.repeat(i)} long title`
          }))
      ]
    }"
    input-hint="long names"
    no-results-hint="no results hint"
    label="some label"
    required
  />

  <h1>CmkDropdownButton</h1>
  <h2>button</h2>
  <CmkDropdownButton>default button</CmkDropdownButton>
  <h2>group</h2>
  <CmkDropdownButton group="start">start</CmkDropdownButton
  ><CmkDropdownButton group="end">end</CmkDropdownButton>
</template>
