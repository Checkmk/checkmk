<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import { useInjectIsPublicDashboard } from '@/dashboard/composables/useIsPublicDashboard'
import type { IFrameContent, SidebarElementContent } from '@/dashboard/types/widget.ts'

import DashboardContentContainer from './DashboardContentContainer.vue'
import DashboardContentIFrame from './DashboardContentIFrame.vue'
import type { ContentProps } from './types.ts'

const { _t } = usei18n()

const props = defineProps<ContentProps<SidebarElementContent>>()
const isPublicDashboard = useInjectIsPublicDashboard()

const iFrameProps = computed(() => {
  const urlParams = new URLSearchParams({
    name: props.content.name
  }).toString()
  const iFrameContent: IFrameContent = {
    type: 'url',
    url: `widget_iframe_sidebar.py?${urlParams}`
  }
  return {
    ...props,
    content: iFrameContent
  } as ContentProps<IFrameContent>
})
</script>

<template>
  <DashboardContentContainer
    v-if="isPublicDashboard"
    :effective-title="effectiveTitle"
    :general_settings="general_settings"
  >
    <div class="db-content-sidebar-element__not-available">
      {{ _t('Not available on shared dashboards') }}
    </div>
  </DashboardContentContainer>
  <DashboardContentIFrame v-else v-bind="iFrameProps" />
</template>

<style scoped>
.db-content-sidebar-element__not-available {
  padding: var(--spacing);
  color: var(--font-color);
}
</style>
