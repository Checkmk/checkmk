<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkHtml from '@/components/CmkHtml.vue'
import HelpText from '@/components/HelpText.vue'
import CmkSpace from '@/components/CmkSpace.vue'
import { type TextWidgetProps } from './widget_types'

defineProps<TextWidgetProps>()
</script>

<template>
  <span class="qs-text-widget">
    <CmkHtml :html="text" />
    <template v-if="tooltip">
      <CmkSpace :size="'small'" />
      <HelpText :help="tooltip" />
    </template>
  </span>
</template>

<style scoped>
.qs-text-widget {
  margin-bottom: var(--spacing);
}
</style>
