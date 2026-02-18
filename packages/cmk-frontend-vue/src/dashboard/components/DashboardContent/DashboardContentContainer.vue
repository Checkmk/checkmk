<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import CmkScrollContainer from '@/components/CmkScrollContainer.vue'

import { useInjectIsPublicDashboard } from '@/dashboard/composables/useIsPublicDashboard'
import type { WidgetGeneralSettings } from '@/dashboard/types/widget'

interface DashboardContentContainerProps {
  effectiveTitle: string | undefined
  general_settings: WidgetGeneralSettings
  contentOverflow?: string
  contentCenter?: boolean
  isScrollablePreview?: boolean
}

const {
  effectiveTitle,
  general_settings: generalSettings,
  contentOverflow = 'auto',
  contentCenter = false,
  isScrollablePreview = false
} = defineProps<DashboardContentContainerProps>()

const hasBackground = computed<boolean>(() => {
  return !!generalSettings.render_background
})

const isPublicDashboard = useInjectIsPublicDashboard()
</script>

<template>
  <div class="db-content-container">
    <div
      v-if="effectiveTitle && generalSettings.title.render_mode !== 'hidden'"
      class="db-content-container__title"
      :class="{
        'db-content-container__title--with-background':
          generalSettings.title.render_mode === 'with_background'
      }"
      role="heading"
    >
      <a
        v-if="generalSettings.title?.url && !isScrollablePreview && !isPublicDashboard"
        :href="generalSettings.title.url"
        >{{ effectiveTitle }}</a
      >
      <span v-else>{{ effectiveTitle }}</span>
    </div>
    <div
      class="db-content-container__content"
      :class="{
        'db-content-container__content-background': hasBackground,
        'db-content-container__content-center': contentCenter
      }"
    >
      <CmkScrollContainer
        v-if="isScrollablePreview"
        height="calc(calc(var(--dimension-8) * 10) - var(--dimension-8))"
        class="db-content-container__preview-scroll-container"
      >
        <div class="db-content-container__preview-click-shield">
          <slot />
        </div>
      </CmkScrollContainer>
      <slot v-else />
    </div>
  </div>
</template>

<style scoped>
.db-content-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
}

.db-content-container__title {
  height: var(--dimension-8);
  display: flex;
  justify-content: center;
  align-items: center;

  a {
    text-decoration: none;

    &:hover {
      text-decoration: underline;
    }
  }

  &.db-content-container__title--with-background {
    background-color: var(--ux-theme-5);
  }
}

.db-content-container__content {
  display: flex;
  flex: 1;
  flex-direction: column;
  overflow: v-bind('contentOverflow');

  &.db-content-container__content-background {
    background-color: var(--db-content-bg-color);
  }

  &.db-content-container__content-center {
    justify-content: center;
    align-items: center;
  }
}

/* This max-width is only needed for the preview of 'url' widgets, i.e. plain
   DashboardContentIFrame, which in preview mode always overflow this container */
.db-content-container__preview-scroll-container {
  max-width: 720px;
}

.db-content-container__preview-click-shield {
  pointer-events: none;
}
</style>
