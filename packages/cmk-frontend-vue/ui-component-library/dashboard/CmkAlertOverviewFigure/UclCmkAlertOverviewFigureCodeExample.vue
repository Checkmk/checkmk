<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlertOverviewFigure from '@/dashboard/components/figures/CmkAlertOverviewFigure.vue'
import type { AlertOverview } from '@/dashboard/types/widget'

const value: AlertOverview = {
  elements: [
    {
      site_id: 'heute',
      host_name: 'myhost',
      service_description: 'CPU load',
      num_ok: 2,
      num_warn: 1,
      num_crit: 1,
      num_unknown: 0,
      num_problems: 2,
      links: [],
      link_properties: { links: [] }
    }
  ]
}
</script>

<template>
  <CmkAlertOverviewFigure
    :value="value"
    :width="300"
    :height="150"
    :filters="{}"
    :interactive="false"
  />
</template>
