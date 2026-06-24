<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { SplitterGroup, SplitterPanel, SplitterResizeHandle } from 'reka-ui'
import { computed, useTemplateRef, watch } from 'vue'

interface PanelInstance {
  collapse: () => void
  expand: () => void
  isCollapsed: boolean
}

export interface CmkSplitPaneProps {
  rightMinSize?: number
  rightMaxSize?: number
  rightDefaultSize?: number
  sizeUnit?: '%' | 'px'
  keyboardResizeBy?: number
  hideHandleWhenCollapsed?: boolean
  collapsibleOnResize?: boolean
}

const {
  rightMinSize = 20,
  rightMaxSize = 50,
  rightDefaultSize = 30,
  sizeUnit = '%',
  keyboardResizeBy = 10,
  hideHandleWhenCollapsed = true,
  collapsibleOnResize = true
} = defineProps<CmkSplitPaneProps>()

const collapsed = defineModel<boolean>('collapsed', { default: false })

const rightPanel = useTemplateRef<PanelInstance>('rightPanel')

const hidePanel = computed(() => collapsed.value && !collapsibleOnResize)

watch(
  [collapsed, rightPanel],
  ([value, panel]) => {
    if (!panel || !collapsibleOnResize) {
      return
    }
    if (value && !panel.isCollapsed) {
      panel.collapse()
    } else if (!value && panel.isCollapsed) {
      panel.expand()
    }
  },
  { immediate: true, flush: 'post' }
)

function onCollapse(): void {
  collapsed.value = true
}

function onExpand(): void {
  collapsed.value = false
}

function focusHandle(event: PointerEvent): void {
  ;(event.currentTarget as HTMLElement | null)?.focus()
}
</script>

<template>
  <SplitterGroup
    direction="horizontal"
    :keyboard-resize-by="keyboardResizeBy"
    class="cmk-split-pane"
  >
    <SplitterPanel class="cmk-split-pane__panel">
      <slot name="left" />
    </SplitterPanel>

    <SplitterResizeHandle
      v-show="!(collapsed && hideHandleWhenCollapsed)"
      class="cmk-split-pane__handle"
      @pointerdown="focusHandle"
    >
      <span class="cmk-split-pane__grip" aria-hidden="true">
        <span class="cmk-split-pane__bar" />
        <span class="cmk-split-pane__bar" />
      </span>
    </SplitterResizeHandle>

    <SplitterPanel
      v-show="!hidePanel"
      ref="rightPanel"
      :collapsible="collapsibleOnResize"
      :collapsed-size="0"
      :min-size="rightMinSize"
      :max-size="rightMaxSize"
      :default-size="rightDefaultSize"
      :size-unit="sizeUnit"
      class="cmk-split-pane__panel"
      @collapse="onCollapse"
      @expand="onExpand"
    >
      <slot name="right" />
    </SplitterPanel>
  </SplitterGroup>
</template>

<style scoped>
.cmk-split-pane {
  display: flex;
  width: 100%;
  height: 100%;
}

.cmk-split-pane__panel {
  overflow: auto;
}

.cmk-split-pane__handle {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  width: var(--dimension-3);
  border-left: 4px solid var(--ux-theme-6);
  cursor: col-resize;
  outline: none;
}

.cmk-split-pane__handle:focus-visible {
  outline: 1px solid var(--success);
  outline-offset: -1px;
}

.cmk-split-pane__grip {
  display: flex;
  gap: var(--dimension-2);
  margin-left: var(--dimension-5);
}

.cmk-split-pane__bar {
  width: var(--dimension-3);
  height: 36px;
  background-color: var(--success);
  border-radius: 2px;
}
</style>
