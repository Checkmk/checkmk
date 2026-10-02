<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkSiteOverviewSitesFigure from '@/dashboard/components/figures/CmkSiteOverviewSitesFigure.vue'
import type { SiteOverviewSites } from '@/dashboard/types/widget'

const value: SiteOverviewSites = {
  mode: 'sites',
  links: [],
  sites: [
    {
      status: 'online',
      site_id: 'heute',
      alias: 'Local site',
      parts: [
        { category: 'critical', count: 1 },
        { category: 'unknown', count: 0 },
        { category: 'warning', count: 2 },
        { category: 'downtime', count: 0 },
        { category: 'ok', count: 40 }
      ],
      link_properties: { links: [] }
    }
  ]
}
</script>

<template>
  <CmkSiteOverviewSitesFigure
    :value="value"
    :width="300"
    :height="150"
    hexagon-size="default"
    :filters="{}"
    :interactive="false"
  />
</template>
