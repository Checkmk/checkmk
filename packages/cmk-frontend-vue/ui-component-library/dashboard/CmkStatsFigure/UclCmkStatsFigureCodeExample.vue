<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkStatsFigure from '@/dashboard/components/figures/CmkStatsFigure.vue'
import type { Stats } from '@/dashboard/types/widget'

const value: Stats = {
  links: [],
  parts: [
    { category: 'up', count: 12, link_properties: { links: [] } },
    { category: 'downtime', count: 1, link_properties: { links: [] } },
    { category: 'unreachable', count: 0, link_properties: { links: [] } },
    { category: 'down', count: 2, link_properties: { links: [] } }
  ],
  total: { count: 15, link_properties: { links: [] } }
}
</script>

<template>
  <CmkStatsFigure :value="value" :width="400" :height="200" :filters="{}" :interactive="false" />
</template>
