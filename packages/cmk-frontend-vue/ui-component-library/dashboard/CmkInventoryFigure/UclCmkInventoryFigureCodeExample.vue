<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkInventoryFigure from '@/dashboard/components/figures/CmkInventoryFigure.vue'
import type { InventoryAttribute } from '@/dashboard/types/widget'

const value: InventoryAttribute = {
  links: [],
  link_properties: { links: [] },
  value: 'Ubuntu 24.04'
}
</script>

<template>
  <CmkInventoryFigure
    :value="value"
    :width="300"
    :height="150"
    :filters="{}"
    :interactive="false"
  />
</template>
