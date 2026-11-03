<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkResizeHandle from 'cmk-ui-library/components/CmkResizeHandle.vue'
import { SplitterGroup, SplitterPanel, SplitterResizeHandle } from 'reka-ui'
import { computed, useTemplateRef, watch } from 'vue'

interface PanelInstance {
  collapse: () => void
  expand: () => void
  isCollapsed: boolean
}

export interface CmkSplitPaneProps {
  paneMinSize?: number
  paneMaxSize?: number
  paneDefaultSize?: number
  paneMinWidth?: string | undefined
  dock?: 'left' | 'right'
  sizeUnit?: '%' | 'px'
  keyboardResizeBy?: number
  hideHandleWhenCollapsed?: boolean
  collapsibleOnResize?: boolean
}

const {
  paneMinSize = 20,
  paneMaxSize = 50,
  paneDefaultSize = 30,
  paneMinWidth,
  dock = 'right',
  sizeUnit = '%',
  keyboardResizeBy = 10,
  hideHandleWhenCollapsed = true,
  collapsibleOnResize = true
} = defineProps<CmkSplitPaneProps>()

const collapsed = defineModel<boolean>('collapsed', { default: false })

const emit = defineEmits<{
  resize: [size: number]
}>()

const leftPanel = useTemplateRef<PanelInstance>('leftPanel')
const rightPanel = useTemplateRef<PanelInstance>('rightPanel')
const dockedPanel = computed(() => (dock === 'left' ? leftPanel.value : rightPanel.value))

const hidePanel = computed(() => collapsed.value && !collapsibleOnResize)

watch(
  [collapsed, dockedPanel],
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

function panelProps(side: 'left' | 'right') {
  if (side !== dock) {
    return { class: 'cmk-split-pane__panel' }
  }
  return {
    class: 'cmk-split-pane__panel',
    collapsible: collapsibleOnResize,
    collapsedSize: 0,
    minSize: paneMinSize,
    maxSize: paneMaxSize,
    defaultSize: paneDefaultSize,
    sizeUnit,
    style: { minWidth: paneMinWidth, display: hidePanel.value ? 'none' : undefined },
    onCollapse,
    onExpand,
    onResize: (size: number) => emit('resize', size)
  }
}

function focusHandle(event: PointerEvent): void {
  ;(event.currentTarget as HTMLElement | null)?.focus()
}
</script>

<template>
  <SplitterGroup
    :key="dock"
    direction="horizontal"
    :keyboard-resize-by="keyboardResizeBy"
    class="cmk-split-pane"
  >
    <SplitterPanel ref="leftPanel" v-bind="panelProps('left')">
      <slot name="left" />
    </SplitterPanel>

    <SplitterResizeHandle
      v-show="!(collapsed && hideHandleWhenCollapsed)"
      class="cmk-split-pane__handle"
      :class="{ 'cmk-split-pane__handle--dock-left': dock === 'left' }"
      @pointerdown="focusHandle"
    >
      <CmkResizeHandle class="cmk-split-pane__grip" />
    </SplitterResizeHandle>

    <SplitterPanel ref="rightPanel" v-bind="panelProps('right')">
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
  position: relative;
  box-sizing: border-box;
  width: var(--dimension-6);
  border-left: var(--dimension-2) solid var(--cmk-split-pane-border-color);
  cursor: col-resize;
  outline: none;
}

.cmk-split-pane__handle:hover,
.cmk-split-pane__handle:active {
  border-left-color: var(--cmk-split-pane-border-color-active);
}

.cmk-split-pane__handle--dock-left {
  border-right: var(--dimension-2) solid var(--cmk-split-pane-border-color);
  border-left: none;
}

.cmk-split-pane__handle--dock-left:hover,
.cmk-split-pane__handle--dock-left:active {
  border-right-color: var(--cmk-split-pane-border-color-active);
}

.cmk-split-pane__handle:focus-visible {
  outline: 1px solid var(--success);
  outline-offset: -1px;
}

.cmk-split-pane__grip {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
}

body[data-theme='facelift'] .cmk-split-pane__handle {
  --cmk-split-pane-border-color: var(--color-mid-grey-10);
  --cmk-split-pane-border-color-active: var(--color-mid-grey-50);
}

body[data-theme='modern-dark'] .cmk-split-pane__handle {
  --cmk-split-pane-border-color: var(--color-mid-grey-90);
  --cmk-split-pane-border-color-active: var(--color-mid-grey-60);
}
</style>
