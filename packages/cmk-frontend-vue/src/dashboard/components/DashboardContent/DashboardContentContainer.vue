<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import type { WidgetGeneralSettings } from '@/dashboard/types/widget'

interface DashboardContentContainerProps {
  effectiveTitle: string | undefined
  general_settings: WidgetGeneralSettings
  contentOverflow?: string
  contentCenter?: boolean
}

const {
  effectiveTitle,
  general_settings: generalSettings,
  contentOverflow = 'auto',
  contentCenter = false
} = defineProps<DashboardContentContainerProps>()

const hasBackground = computed<boolean>(() => {
  return !!generalSettings.render_background
})

const displayTitle = computed<string | undefined>(() => {
  if (effectiveTitle) {
    return effectiveTitle
  }
  if (generalSettings.title.text && generalSettings.title.render_mode !== 'hidden') {
    return generalSettings.title.text
  }
  return undefined
})
</script>

<template>
  <div class="db-content-container">
    <div
      v-if="displayTitle && generalSettings.title.render_mode !== 'hidden'"
      class="db-content-container__title"
      :class="{
        'db-content-container__title--with-background':
          generalSettings.title.render_mode === 'with_background'
      }"
      role="heading"
    >
      <a v-if="generalSettings.title?.url" :href="generalSettings.title.url">{{ displayTitle }}</a>
      <span v-else>{{ displayTitle }}</span>
    </div>
    <div
      class="db-content-container__content"
      :class="{
        'db-content-container__content-background': hasBackground,
        'db-content-container__content-center': contentCenter
      }"
    >
      <slot />
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
  height: 22px;
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
</style>
