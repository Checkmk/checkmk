<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import usei18n from 'cmk-ui-library/lib/i18n'
import { useResizeObserver } from 'cmk-ui-library/lib/useResizeObserver'
import { computed, ref, useTemplateRef } from 'vue'

const { _t } = usei18n()

const COLLAPSED_HEIGHT_PX = 300
const MIN_HIDDEN_HEIGHT_PX = 60

const isExpanded = ref(false)
const contentHeight = ref(0)
const contentEl = useTemplateRef<HTMLElement>('content')

const { observe } = useResizeObserver(() => {
  contentHeight.value = contentEl.value?.offsetHeight ?? 0
})
observe(contentEl)

const shouldShowToggle = computed(
  () => contentHeight.value - COLLAPSED_HEIGHT_PX > MIN_HIDDEN_HEIGHT_PX
)
const clipStyle = computed(() =>
  shouldShowToggle.value && !isExpanded.value
    ? { maxHeight: `${COLLAPSED_HEIGHT_PX}px` }
    : undefined
)

const toggleExpansion = () => {
  isExpanded.value = !isExpanded.value
}
</script>

<template>
  <div class="global-settings-collapsible-value">
    <div class="global-settings-collapsible-value__clip" :style="clipStyle">
      <div ref="content">
        <slot />
      </div>
      <div
        v-if="shouldShowToggle && !isExpanded"
        class="global-settings-collapsible-value__fade-overlay"
      ></div>
    </div>
    <CmkButton
      v-if="shouldShowToggle"
      size="small"
      :icon="{ name: 'tree-closed', rotate: isExpanded ? -90 : 90, size: 'small' }"
      class="global-settings-collapsible-value__toggle-button"
      :class="{ 'global-settings-collapsible-value__toggle-button--overlay': !isExpanded }"
      @click.stop="toggleExpansion"
    >
      {{ isExpanded ? _t('Show less') : _t('Show more') }}
    </CmkButton>
  </div>
</template>

<style scoped>
.global-settings-collapsible-value {
  display: grid;
  width: fit-content;
  max-width: 100%;
  min-width: 0;
}

.global-settings-collapsible-value__clip {
  grid-area: 1 / 1;
  position: relative;
  overflow: hidden;
}

.global-settings-collapsible-value__fade-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 100px;
  background: linear-gradient(transparent, var(--global-settings-collapsible-value-bg-color));
  pointer-events: none;
}

.global-settings-collapsible-value__toggle-button {
  position: relative;
  justify-self: center;
  margin: var(--dimension-3) 0;
}

.global-settings-collapsible-value__toggle-button--overlay {
  grid-area: 1 / 1;
  align-self: end;
}
</style>
