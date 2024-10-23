<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'
import DropDown from '@/components/DropDown.vue'
const data = ref<string>('init')
</script>

<template>
  <DropDown
    v-model:selected-option="data"
    :options="[
      { ident: 'init', name: 'selected by default' },
      { ident: '2', name: 'two' }
    ]"
    input_hint="some input hint"
    component-id="some component id"
  />
</template>
