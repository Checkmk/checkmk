<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkIcon from 'cmk-ui-library/components/CmkIcon/CmkIcon.vue'
import type { SimpleIcons } from 'cmk-ui-library/components/CmkIcon/types'
import CmkIconLink from 'cmk-ui-library/components/CmkIconLink.vue'
import { type CSSProperties, computed } from 'vue'

import type { MonitoringIcon } from '@/monitoring/shared/api/types'

import { ICON_LIST_GAP, ICON_LIST_ICON_SIZE, iconListWidth } from './iconList'

const props = defineProps<{
  icons: MonitoringIcon[]
  maxPerRow?: number | undefined
}>()

const gap = `${ICON_LIST_GAP}px`
const iconSize = `${ICON_LIST_ICON_SIZE}px`

const listStyle = computed<CSSProperties>(() =>
  props.maxPerRow === undefined ? {} : { maxWidth: `${iconListWidth(props.maxPerRow)}px` }
)
</script>

<template>
  <div class="monitoring-icon-list" :style="listStyle">
    <template v-for="icon in icons" :key="icon.icon_name">
      <CmkIconLink
        v-if="icon.link"
        class="monitoring-icon-list__item"
        :name="icon.icon_name as SimpleIcons"
        :title="icon.title"
        :href="icon.link"
        target="_top"
        size="medium"
      />
      <span v-else class="monitoring-icon-list__item" :title="icon.title">
        <CmkIcon :name="icon.icon_name as SimpleIcons" :title="icon.title" size="medium" />
      </span>
    </template>
  </div>
</template>

<style scoped>
.monitoring-icon-list {
  display: flex;
  flex-flow: row wrap;
  align-items: center;
  gap: v-bind(gap);
}

.monitoring-icon-list__item {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
}

/* stylelint-disable-next-line selector-pseudo-class-no-unknown, checkmk/vue-bem-naming-convention */
.monitoring-icon-list__item :deep(.cmk-icon) {
  width: v-bind(iconSize);
  height: v-bind(iconSize);
}
</style>
