<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkZebra from '@/components/CmkZebra.vue'

defineProps<{ screenshotMode: boolean }>()

const demoItems = [
  {
    id: 1,
    title: 'Configuration change: Updated host monitoring settings'
  },
  {
    id: 2,
    title: 'Rule modification: Changed notification rules for critical alerts'
  },
  {
    id: 3,
    title: 'Service discovery: Added new services for web servers'
  },
  {
    id: 4,
    title: 'Contact group update: Modified emergency contact settings'
  },

  {
    id: 5,
    title: 'Performance tuning: Adjusted check intervals for database monitoring'
  }
]
</script>

<template>
  <div>
    <div v-for="(item, idx) in demoItems" :key="item.id">
      <CmkZebra :num="idx" class="demo-cmk-zebra">
        {{ item.title }}
      </CmkZebra>
    </div>
  </div>
</template>

<style scoped>
.demo-cmk-zebra {
  padding: 12px;
  background-color: var(--default-bg-color, transparent);
  width: 50%;
}
</style>
