<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkSiteOverviewHostsFigure from '@/dashboard/components/figures/CmkSiteOverviewHostsFigure.vue'
import type { SiteOverviewHosts } from '@/dashboard/types/widget'

const value: SiteOverviewHosts = {
  mode: 'hosts',
  links: [],
  hosts: [
    {
      site_id: 'heute',
      host_name: 'myhost',
      state: 'UP',
      has_been_checked: true,
      in_downtime: false,
      num_services: 10,
      num_warn: 1,
      num_crit: 0,
      num_unknown: 0,
      link_properties: { links: [] }
    }
  ]
}
</script>

<template>
  <CmkSiteOverviewHostsFigure
    :value="value"
    :width="300"
    :height="150"
    hexagon-size="default"
    :filters="{}"
    :interactive="false"
  />
</template>
