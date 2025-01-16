<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkHtml from '@/components/CmkHtml.vue'
import ToolTip from '@/quick-setup/components/ToolTip.vue'

import { type TextWidgetProps } from './widget_types'

defineProps<TextWidgetProps>()
</script>

<template>
  <span class="qs-text-widget">
    <CmkHtml :html="text" />
    <ToolTip v-if="tooltip">
      <p>{{ tooltip }}</p>
    </ToolTip>
  </span>
</template>

<style scoped>
.qs-text-widget {
  margin-bottom: var(--spacing);

  ::v-deep(a) {
    pointer-events: all;
  }
}
</style>
