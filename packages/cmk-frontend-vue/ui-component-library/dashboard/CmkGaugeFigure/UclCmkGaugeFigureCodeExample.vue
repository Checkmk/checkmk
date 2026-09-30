<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkGaugeFigure from '@/dashboard/components/figures/CmkGaugeFigure.vue'
import type { Gauge } from '@/dashboard/types/widget'

const value: Gauge = {
  links: [],
  link_properties: { links: [] },
  value: 42,
  unit_format: {
    notation: 'decimal',
    symbol: '%',
    precision: { type: 'auto', digits: 2 },
    convertible: false
  },
  range: { minimum: 0, maximum: 100 },
  samples: [],
  status: { state: 'WARNING', has_been_checked: true, tint_background: false }
}
</script>

<template>
  <CmkGaugeFigure :value="value" :width="300" :height="200" :filters="{}" :interactive="false" />
</template>
