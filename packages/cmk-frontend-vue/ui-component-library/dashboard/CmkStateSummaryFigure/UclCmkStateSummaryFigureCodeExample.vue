<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkStateSummaryFigure from '@/dashboard/components/figures/CmkStateSummaryFigure.vue'
import type { StateSummary } from '@/dashboard/types/widget'

const value: StateSummary = {
  links: [],
  in_state: { count: 3, link_properties: { links: [] } },
  total: 10
}
</script>

<template>
  <CmkStateSummaryFigure
    :value="value"
    :width="300"
    :height="200"
    :filters="{}"
    :interactive="false"
  />
</template>
