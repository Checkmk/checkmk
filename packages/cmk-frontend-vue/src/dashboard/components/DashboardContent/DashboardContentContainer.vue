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
  contentCenter?: boolean
}

const {
  effectiveTitle,
  general_settings: generalSettings,
  contentCenter = false
} = defineProps<DashboardContentContainerProps>()

const titleRenderClass = computed<string>(() => {
  if (generalSettings.title?.render_mode === 'with_background') {
    return 'db-content-container__title--with-background'
  }
  return ''
})

const hasBackground = computed<boolean>(() => {
  return !!generalSettings.render_background
})
</script>

<template>
  <div class="db-content-container">
    <div
      v-if="effectiveTitle && generalSettings.title?.render_mode !== 'hidden'"
      class="db-content-container__title"
      :class="titleRenderClass"
      role="heading"
    >
      <a v-if="generalSettings.title?.url" :href="generalSettings.title.url">{{
        effectiveTitle
      }}</a>
      <span v-else>{{ effectiveTitle }}</span>
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
    background-color: var(--headline-color);
  }
}

.db-content-container__content {
  display: flex;
  flex: 1;
  flex-direction: column;
  overflow: auto;

  &.db-content-container__content-background {
    background-color: var(--db-content-bg-color);
  }

  &.db-content-container__content-center {
    justify-content: center;
    align-items: center;
  }
}
</style>
