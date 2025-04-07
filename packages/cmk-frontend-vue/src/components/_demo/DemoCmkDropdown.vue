<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'
import CmkDropdown from '@/components/CmkDropdown.vue'
import CmkSpace from '@/components/CmkSpace.vue'

defineProps<{ screenshotMode: boolean }>()

const defaultSelected = ref<string>('init')
const defaultSelected2 = ref<string>('init')
const defaultEmpty1 = ref<string | null>(null)
const defaultEmpty2 = ref<string | null>(null)
const defaultEmpty3 = ref<string | null>(null)
</script>

<template>
  <CmkDropdown
    v-model:selected-option="defaultSelected2"
    :options="{ type: 'fixed', suggestions: [{ name: 'init', title: 'single element' }] }"
    input-hint="some input hint"
    no-results-hint="no results hint"
    component-id="some component id"
    required-text="required"
    label="some label"
  />
  <CmkSpace />
  <CmkDropdown
    v-model:selected-option="defaultSelected"
    :options="{
      type: 'fixed',
      suggestions: [
        { name: 'init', title: 'selected by default' },
        { name: '2', title: 'two' }
      ]
    }"
    input-hint="some input hint"
    no-results-hint="no results hint"
    component-id="some component id"
    required-text="required"
    label="some label"
  />
  <CmkSpace />
  <CmkDropdown
    v-model:selected-option="defaultEmpty1"
    :options="{
      type: 'fixed',
      suggestions: [
        { name: '1', title: 'one' },
        { name: '2', title: 'two' }
      ]
    }"
    input-hint="some input hint"
    no-results-hint="no results hint"
    component-id="some component id"
    label="some label"
  />
  <CmkSpace />
  <CmkDropdown
    v-model:selected-option="defaultEmpty2"
    :options="{ type: 'filtered', suggestions: [] }"
    input-hint="some input hint"
    no-results-hint="no results hint"
    component-id="some component id"
    required-text="required"
    label="some label"
  />
  <CmkSpace />
  <CmkDropdown
    v-model:selected-option="defaultEmpty3"
    :options="{
      type: 'filtered',
      suggestions: [
        ...Array(20)
          .fill(0)
          .map((_, i) => ({ name: i.toString(), title: i.toString() }))
      ]
    }"
    input-hint="long dropdown"
    no-results-hint="no results hint"
    component-id="some component id"
    required-text="required"
    label="some label"
  />
</template>
