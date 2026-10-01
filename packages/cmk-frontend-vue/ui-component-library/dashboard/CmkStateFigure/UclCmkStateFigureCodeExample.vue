<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkStateFigure from '@/dashboard/components/figures/CmkStateFigure.vue'
import type { ObjectState } from '@/dashboard/types/widget'

const value: ObjectState = {
  links: [],
  link_properties: { links: [] },
  state: 'CRITICAL',
  has_been_checked: true,
  tint_background: true,
  plugin_output: 'CPU load is 4.2 (warn/crit at 2.0/4.0)'
}
</script>

<template>
  <CmkStateFigure :value="value" :width="300" :height="200" :filters="{}" :interactive="false" />
</template>
