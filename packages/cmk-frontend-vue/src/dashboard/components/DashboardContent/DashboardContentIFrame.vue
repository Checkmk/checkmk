<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { type Ref, computed, useTemplateRef, watch } from 'vue'

import { useInjectIsPublicDashboard } from '@/dashboard/composables/useIsPublicDashboard'
import { dashboardTimeRangeMessage } from '@/dashboard/lib/dashboardTimeRangeMessage'
import { iframeUrl } from '@/dashboard/lib/iframeUrl'
import { type IFrameContent } from '@/dashboard/types/widget.ts'

import DashboardContentContainer from './DashboardContentContainer.vue'
import type { ContentProps } from './types.ts'

const { _t } = usei18n()

interface DashboardContentIFrameProps extends ContentProps<IFrameContent> {
  contentCenter?: boolean
  disableClickShield?: boolean
}

const {
  content,
  contentCenter,
  disableClickShield = false,
  effective_filter_context: effectiveFilterContext,
  range,
  tick
} = defineProps<DashboardContentIFrameProps>()
const isPublicDashboard = useInjectIsPublicDashboard()

const hasUrl: Ref<boolean> = computed(() => content.url.trim() !== '')

const isValidUrl: Ref<boolean> = computed(() => {
  try {
    return ['https:', 'http:'].includes(new URL(content.url, window.location.origin).protocol)
  } catch {
    return false
  }
})

const showsIframe: Ref<boolean> = computed(() => hasUrl.value && isValidUrl.value)

const src = computed(() =>
  iframeUrl(content.url, {
    context: content.include_context ? effectiveFilterContext.filters : null,
    timeRange: content.include_time_range ? range : null
  })
)

const iframe = useTemplateRef<HTMLIFrameElement>('iframe')

function postTimeRange(): void {
  iframe.value?.contentWindow?.postMessage(
    dashboardTimeRangeMessage(range, tick),
    new URL(src.value, window.location.origin).origin
  )
}

watch(() => [range, tick], postTimeRange)
</script>

<template>
  <DashboardContentContainer
    :effective-title="effectiveTitle"
    :general_settings="general_settings"
    :content-center="contentCenter"
    :is-scrollable-preview="isPreview && showsIframe"
  >
    <div
      class="db-content-i-frame__div"
      :class="{
        'db-content-i-frame__preview': isPreview && showsIframe
      }"
    >
      <iframe
        v-if="showsIframe"
        :key="src"
        ref="iframe"
        class="db-content-i-frame__iframe"
        allowtransparency="true"
        :src="src"
        @load="postTimeRange"
      />
      <div v-else-if="hasUrl" class="db-content-i-frame__invalid-url">{{ _t('Invalid URL') }}</div>
      <div
        v-if="isPublicDashboard && !disableClickShield"
        class="db-content-i-frame__click-shield"
      />
    </div>
  </DashboardContentContainer>
</template>

<style scoped>
.db-content-i-frame__div {
  position: relative;
  height: 100%;
  overflow: hidden;
  -webkit-overflow-scrolling: touch;
}

.db-content-i-frame__click-shield {
  position: absolute;
  inset: 0;
  z-index: 1;
}

.db-content-i-frame__iframe {
  height: 100%;
  width: 100%;
  border: none;
}

/* Overflowing of this preview iframe is handled in DashboardContentContainer's scroll container */
.db-content-i-frame__preview,
.db-content-i-frame__preview .db-content-i-frame__iframe {
  width: 100vw;
  height: 100vh;
}

.db-content-i-frame__invalid-url {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--default-font-color);
}
</style>
