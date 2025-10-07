<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkSpace from '@/components/CmkSpace.vue'

const selectedIcon = defineModel<string | null>('selectedIcon', { required: false, default: null })
const selectedEmblem = defineModel<string | null>('selectedEmblem', {
  required: false,
  default: null
})
</script>

<template>
  <span v-if="selectedIcon">{{ selectedIcon }}</span>
  <span v-if="selectedIcon && selectedEmblem"><CmkSpace /> + <CmkSpace /></span>
  <span v-if="selectedEmblem">{{ selectedEmblem }}</span>
</template>
