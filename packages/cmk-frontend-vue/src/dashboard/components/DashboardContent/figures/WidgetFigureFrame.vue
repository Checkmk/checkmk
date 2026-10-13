<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts" generic="T">
import CmkSurfaceNotice from 'cmk-ui-library/components/CmkSurfaceNotice.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { LOADING_AFFORDANCE_DELAY_MS, useDelayedFlag } from 'cmk-ui-library/lib/useDelayedFlag'
import { useResizeObserver } from 'cmk-ui-library/lib/useResizeObserver'
import { ref } from 'vue'

import type { WidgetDataState } from '@/dashboard/composables/useWidgetData'
import type { WidgetGeneralSettings } from '@/dashboard/types/widget'

import DashboardContentContainer from '../DashboardContentContainer.vue'

const props = defineProps<{
  effectiveTitle: string | undefined
  general_settings: WidgetGeneralSettings
  state: WidgetDataState<T>
}>()

defineEmits<{ retry: [] }>()

defineSlots<{
  default(props: { value: T; width: number; height: number }): unknown
}>()

const { _t } = usei18n()

const box = ref<HTMLElement | null>(null)
const width = ref(0)
const height = ref(0)

const { observe } = useResizeObserver((entries) => {
  const size = entries[0]?.contentBoxSize[0]
  if (size) {
    width.value = size.inlineSize
    height.value = size.blockSize
  }
})
observe(box)

const showLoading = useDelayedFlag(
  () => props.state.kind === 'loading',
  LOADING_AFFORDANCE_DELAY_MS
)
</script>

<template>
  <DashboardContentContainer
    :effective-title="effectiveTitle"
    :general_settings="general_settings"
    content-overflow="hidden"
  >
    <div ref="box" class="db-widget-figure-frame">
      <div
        v-if="state.kind === 'data' && width > 0 && height > 0"
        class="db-widget-figure-frame__figure"
      >
        <slot :value="state.value" :width="width" :height="height" />
      </div>
      <CmkSurfaceNotice
        v-else-if="state.kind === 'error'"
        class="db-widget-figure-frame__notice"
        variant="error"
        :message="_t('Widget data could not be loaded.')"
        :description="state.detail"
        retry
        @retry="$emit('retry')"
      />
      <CmkSurfaceNotice
        v-else-if="state.kind === 'no-data'"
        class="db-widget-figure-frame__notice"
        variant="warning"
        :message="state.detail"
      />
      <CmkSurfaceNotice
        v-else-if="state.kind === 'loading' && showLoading"
        class="db-widget-figure-frame__notice"
        variant="loading"
        :message="_t('Loading data …')"
      />
    </div>
  </DashboardContentContainer>
</template>

<style scoped>
.db-widget-figure-frame {
  position: relative;
  display: flex;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.db-widget-figure-frame__figure {
  position: absolute;
  inset: 0;
}

.db-widget-figure-frame__notice {
  margin: auto;
}
</style>
