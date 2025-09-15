<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { StaticTextContent } from '@/dashboard-wip/types/widget.ts'

import DashboardContentContainer from './DashboardContentContainer.vue'
import type { ContentProps } from './types.ts'

const props = defineProps<ContentProps>()
const content = props.content as StaticTextContent
</script>

<template>
  <DashboardContentContainer v-bind="general_settings">
    <div class="db-content-static-text__text">
      {{ content.text }}
    </div>
  </DashboardContentContainer>
</template>

<style scoped>
.db-content-static-text__text {
  padding: var(--spacing);
}
</style>
