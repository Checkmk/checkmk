<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkHtml from '@/components/CmkHtml.vue'

import { useInjectIsPublicDashboard } from '@/dashboard/composables/useIsPublicDashboard'
import type { StaticTextContent } from '@/dashboard/types/widget.ts'

import DashboardContentContainer from './DashboardContentContainer.vue'
import type { ContentProps } from './types.ts'

defineProps<ContentProps<StaticTextContent>>()
const isPublicDashboard = useInjectIsPublicDashboard()
</script>

<template>
  <DashboardContentContainer :effective-title="effectiveTitle" :general_settings="general_settings">
    <div class="db-content-static-text__wrapper">
      <CmkHtml class="db-content-static-text__text" :html="content.text" />
      <div v-if="isPublicDashboard" class="db-content-static-text__click-shield" />
    </div>
  </DashboardContentContainer>
</template>

<style scoped>
.db-content-static-text__wrapper {
  position: relative;
  padding: var(--spacing);
}

.db-content-static-text__click-shield {
  position: absolute;
  inset: 0;
  z-index: 1;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.db-preview-content .db-content-static-text__text {
  overflow: hidden;
}
</style>
