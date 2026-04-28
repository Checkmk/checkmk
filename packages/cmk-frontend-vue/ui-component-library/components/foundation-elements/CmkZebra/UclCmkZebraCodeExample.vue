<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkZebra from '@/components/CmkZebra.vue'

const items = [
  'Demonstration of of row context for index 0',
  'Demonstration of of row context for index 1',
  'Demonstration of of row context for index 2'
]
</script>

<template>
  <CmkZebra v-for="(item, index) in items" :key="index" :num="index">
    {{ item }}
  </CmkZebra>
</template>
