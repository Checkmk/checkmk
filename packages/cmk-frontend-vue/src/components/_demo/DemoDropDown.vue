<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'
import DropDown from '@/components/DropDown.vue'
import CmkSpace from '@/components/CmkSpace.vue'
const defaultSelected = ref<string>('init')
const defaultEmpty1 = ref<string | null>(null)
const defaultEmpty2 = ref<string | null>(null)
</script>

<template>
  <DropDown
    v-model:selected-option="defaultSelected"
    :options="[
      { name: 'init', title: 'selected by default' },
      { name: '2', title: 'two' }
    ]"
    input_hint="some input hint"
    no_results_hint="no results hint"
    component-id="some component id"
  />
  <CmkSpace />
  <DropDown
    v-model:selected-option="defaultEmpty1"
    :options="[
      { name: '1', title: 'one' },
      { name: '2', title: 'two' }
    ]"
    input_hint="some input hint"
    no_results_hint="no results hint"
    component-id="some component id"
  />
  <CmkSpace />
  <DropDown
    v-model:selected-option="defaultEmpty2"
    :options="[]"
    input_hint="some input hint"
    no_results_hint="no results hint"
    component-id="some component id"
  />
</template>
