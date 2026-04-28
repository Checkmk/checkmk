<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import CmkToggleButtonGroup from '@/components/CmkToggleButtonGroup.vue'

const currentView = ref('list')

const viewOptions = [
  { label: 'List View', value: 'list' },
  { label: 'Grid View', value: 'grid' }
]
</script>

<template>
  <CmkToggleButtonGroup v-model="currentView" :options="viewOptions" />
</template>
