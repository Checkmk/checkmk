<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
/**
 * The Indicator column: the active modes of a row, followed by its custom icons without an
 * action. Beyond the first few, a "+N" button reveals the rest, like the labels do.
 */
import CmkButton from 'cmk-ui-library/components/CmkButton/CmkButton.vue'
import CmkDynamicIcon from 'cmk-ui-library/components/CmkIcon/CmkDynamicIcon/CmkDynamicIcon.vue'
import CmkIcon from 'cmk-ui-library/components/CmkIcon/CmkIcon.vue'
import type { SimpleIcons } from 'cmk-ui-library/components/CmkIcon/types'
import CmkIconLink from 'cmk-ui-library/components/CmkIconLink.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref } from 'vue'

import type { CustomIcon, MonitoringIcon } from '../../api/types'
import { customIconSpec } from '../customIcon'
import { ICON_LIST_GAP, ICON_LIST_ICON_SIZE } from '../iconList'
import BaseCell from './BaseCell.vue'

const { _t } = usei18n()

const props = defineProps<{
  modes: MonitoringIcon[]
  icons: CustomIcon[]
  max: number
  columnId?: string | undefined
}>()

const expanded = ref(false)

const total = computed(() => props.modes.length + props.icons.length)
const shown = computed(() => (expanded.value ? total.value : Math.min(props.max, total.value)))
const shownModes = computed(() => props.modes.slice(0, shown.value))
const shownIcons = computed(() => props.icons.slice(0, shown.value - shownModes.value.length))

const gap = `${ICON_LIST_GAP}px`
const iconSize = `${ICON_LIST_ICON_SIZE}px`
</script>

<template>
  <BaseCell :column-id="columnId">
    <template #default>
      <div class="monitoring-indicator-cell">
        <template v-for="mode in shownModes" :key="mode.icon_name">
          <CmkIconLink
            v-if="mode.link"
            class="monitoring-indicator-cell__item"
            :name="mode.icon_name as SimpleIcons"
            :title="mode.title"
            :href="mode.link"
            target="_top"
            size="medium"
          />
          <span v-else class="monitoring-indicator-cell__item" :title="mode.title">
            <CmkIcon :name="mode.icon_name as SimpleIcons" :title="mode.title" size="medium" />
          </span>
        </template>
        <span
          v-for="icon in shownIcons"
          :key="icon.ident"
          class="monitoring-indicator-cell__item"
          :title="icon.title"
        >
          <CmkDynamicIcon :spec="customIconSpec(icon)" :title="icon.title" size="medium" />
        </span>
        <CmkButton
          v-if="shown < total"
          class="monitoring-indicator-cell__overflow"
          size="small"
          variant="text"
          :aria-label="_t('Show all %{count} indicators', { count: total })"
          @click="expanded = true"
        >
          +{{ total - shown }}
        </CmkButton>
        <CmkButton
          v-else-if="expanded"
          class="monitoring-indicator-cell__overflow"
          size="small"
          variant="text"
          @click="expanded = false"
        >
          {{ _t('show less') }}
        </CmkButton>
      </div>
    </template>
  </BaseCell>
</template>

<style scoped>
.monitoring-indicator-cell {
  display: flex;
  flex-flow: row wrap;
  align-items: center;
  gap: v-bind(gap);
}

.monitoring-indicator-cell__item {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
}

/* stylelint-disable-next-line selector-pseudo-class-no-unknown, checkmk/vue-bem-naming-convention */
.monitoring-indicator-cell__item :deep(.cmk-icon) {
  width: v-bind(iconSize);
  height: v-bind(iconSize);
}

.monitoring-indicator-cell__overflow {
  flex: 0 0 auto;
}
</style>
