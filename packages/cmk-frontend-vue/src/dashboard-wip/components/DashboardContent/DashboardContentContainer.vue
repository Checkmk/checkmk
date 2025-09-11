<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import type { WidgetGeneralSettings } from '@/dashboard-wip/types/widget.ts'

export interface DashboardContentContainerProps extends WidgetGeneralSettings {
  contentOverflow?: string
}
</script>

<script setup lang="ts">
const { title, contentOverflow = 'auto', ...props } = defineProps<DashboardContentContainerProps>()

let titleRenderClass: string = 'db-content-container__title--with-background'
if (title && ['hidden', 'without_background'].includes(title.render_mode)) {
  titleRenderClass = ''
}
</script>

<template>
  <div class="db-content-container">
    <div
      v-if="title && title.render_mode !== 'hidden'"
      class="db-content-container__title"
      :class="titleRenderClass"
    >
      <a v-if="title.url" :href="title.url">{{ title.text }}</a>
      <span v-else>{{ title.text }}</span>
    </div>
    <div
      class="db-content-container__content"
      :class="{ 'db-content-container__content-background': !!props.render_background }"
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
  overflow: v-bind('contentOverflow');

  &.db-content-container__content-background {
    background-color: var(--db-content-bg-color);
  }
}
</style>
