<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkBarplotFigure from '@/dashboard/components/figures/CmkBarplotFigure.vue'
import type { Barplot } from '@/dashboard/types/widget'

const value: Barplot = {
  links: [],
  unit_format: {
    notation: 'decimal',
    symbol: '%',
    precision: { type: 'auto', digits: 2 },
    convertible: false
  },
  range: null,
  bars: [
    {
      site_id: 'heute',
      host_name: 'myhost',
      service_description: 'CPU utilization',
      value: 42,
      link_properties: { links: [] }
    }
  ]
}
</script>

<template>
  <CmkBarplotFigure :value="value" :width="300" :height="200" :filters="{}" />
</template>
