<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkCheckbox from '@/components/CmkCheckbox.vue'
import { ref } from 'vue'

defineProps<{ screenshotMode: boolean }>()

const value1 = ref<boolean>(true)
const value2 = ref<boolean>(false)
const value3 = ref<boolean>(false)
</script>

<template>
  <ul>
    <li>
      <CmkCheckbox v-model="value1" label="some checkbox" /> <code>{{ value1 }}</code>
    </li>
    <li>
      <CmkCheckbox v-model="value2" label="some other checkbox" /> <code>{{ value2 }}</code>
    </li>
    <li>checkbox without label: <CmkCheckbox v-model="value3" /></li>
    <li>
      <!-- testing vertical alignment -->
      no label<CmkCheckbox v-model="value3" /><span style="font-size: 30px"
        >huge<CmkCheckbox v-model="value3"
      /></span>
    </li>
  </ul>
</template>
