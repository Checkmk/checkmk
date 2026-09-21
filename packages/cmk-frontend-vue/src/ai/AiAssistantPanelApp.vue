<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { onBeforeUnmount, onMounted, watch } from 'vue'

import usei18n from '@/lib/i18n'
import usePersistentRef from '@/lib/usePersistentRef'

import CmkIcon from '@/components/CmkIcon/CmkIcon.vue'

// the toggle and the panel lives in different frames, so we use local storage to sync them:
// Keep in sync with `cmk.aiAssistant` of cmk-frontend.
const OPEN_STORAGE_KEY = 'cmk-ai-assistant-open'
const POSITION_STORAGE_KEY = 'cmk-ai-assistant-position'
const PANEL_SIZE = '300px'

const DOCK_POSITIONS = ['left', 'right', 'bottom'] as const
type DockPosition = (typeof DOCK_POSITIONS)[number]

const { _t } = usei18n()

function parseDockPosition(value: unknown): DockPosition {
  return DOCK_POSITIONS.find((candidate) => candidate === value) ?? 'right'
}

const open = usePersistentRef(OPEN_STORAGE_KEY, false, (value) => value === true, 'session')
const position = usePersistentRef<DockPosition>(
  POSITION_STORAGE_KEY,
  'right',
  parseDockPosition,
  'local'
)

const dockEdges: { position: DockPosition; label: string; rotate: number }[] = [
  { position: 'left', label: _t('Dock to the left'), rotate: 180 },
  { position: 'bottom', label: _t('Dock to the bottom'), rotate: 90 },
  { position: 'right', label: _t('Dock to the right'), rotate: 0 }
]

function parseStorageValue(value: string | null): unknown {
  return value === null ? null : JSON.parse(value)
}

// e.g. a view in a dashboard iframe, but not the content frame of index.py
function isNestedInIframe(): boolean {
  try {
    return (
      window.parent !== window &&
      !(
        window.parent.location.origin === window.location.origin &&
        window.parent.location.pathname.endsWith('/index.py')
      )
    )
  } catch {
    // accessing the location of a cross-origin parent throws
    return true
  }
}

const renderPanel = !isNestedInIframe()

function onStorage(event: StorageEvent): void {
  if (event.key === OPEN_STORAGE_KEY) {
    open.value = parseStorageValue(event.newValue) === true
  } else if (event.key === POSITION_STORAGE_KEY) {
    position.value = parseDockPosition(parseStorageValue(event.newValue))
  }
}

/* Shrinks `#ai-panel-container`, so that the panel does not overlay the page */
function updateMainAreaInset(isOpen: boolean): void {
  const size = isOpen ? PANEL_SIZE : '0px'
  const style = document.documentElement.style
  style.setProperty('--main-area-inset-right', position.value === 'right' ? size : '0px')
  style.setProperty('--main-area-inset-left', position.value === 'left' ? size : '0px')
  style.setProperty('--main-area-inset-bottom', position.value === 'bottom' ? size : '0px')
  // trigger JavaScript layout flow:
  window.dispatchEvent(new Event('resize'))
}

if (renderPanel) {
  watch([open, position], () => updateMainAreaInset(open.value))

  onMounted(() => {
    window.addEventListener('storage', onStorage)
    updateMainAreaInset(open.value)
  })

  onBeforeUnmount(() => {
    window.removeEventListener('storage', onStorage)
    updateMainAreaInset(false)
  })
}
</script>

<template>
  <div
    v-if="renderPanel && open"
    class="ai-assistant-panel-app"
    :class="`ai-assistant-panel-app--${position}`"
  >
    <div class="ai-assistant-panel-app__header">
      <span>{{ _t('AI assistant') }}</span>
      <div class="ai-assistant-panel-app__controls">
        <button
          v-for="edge in dockEdges"
          :key="edge.position"
          type="button"
          class="ai-assistant-panel-app__dock"
          :title="edge.label"
          :aria-label="edge.label"
          :aria-pressed="position === edge.position"
          @click="position = edge.position"
        >
          <CmkIcon
            name="sidebar-position"
            size="xsmall"
            :rotate="edge.rotate"
            :colored="position === edge.position"
          />
        </button>
        <button
          type="button"
          class="ai-assistant-panel-app__close"
          :title="_t('Close')"
          @click="open = false"
        >
          <CmkIcon :aria-label="_t('Close')" name="close" size="xxsmall" />
        </button>
      </div>
    </div>
    <div class="ai-assistant-panel-app__body">
      {{ _t('The AI assistant will live here.') }}
    </div>
  </div>
</template>

<style scoped>
.ai-assistant-panel-app {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  /* stylelint-disable-next-line color-function-notation -- $navigation-bg-color of facelift */
  background-color: rgb(239, 239, 245);
}

:global(body[data-theme='modern-dark'] .ai-assistant-panel-app) {
  /* stylelint-disable-next-line color-function-notation -- $navigation-bg-color of modern-dark */
  background-color: rgb(17, 24, 29);
}

/* The panel fills exactly the inset it reserves in `#ai-panel-container`, so the size is
   only defined once, in `PANEL_SIZE`. */
.ai-assistant-panel-app--right {
  left: auto;
  width: var(--main-area-inset-right);
}

.ai-assistant-panel-app--left {
  right: auto;
  width: var(--main-area-inset-left);
}

.ai-assistant-panel-app--bottom {
  top: auto;
  height: var(--main-area-inset-bottom);
}

.ai-assistant-panel-app__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--dimension-4);
  border-bottom: 1px solid var(--ux-theme-6);
}

.ai-assistant-panel-app__controls {
  display: flex;
  align-items: center;
  gap: var(--dimension-2);
}

.ai-assistant-panel-app__dock,
.ai-assistant-panel-app__close {
  display: flex;
  align-items: center;
  padding: 0;
  border: none;
  background: none;
  color: inherit;
  cursor: pointer;
}

.ai-assistant-panel-app__dock:hover {
  opacity: 0.7;
}

.ai-assistant-panel-app__dock[aria-pressed='true'] {
  cursor: default;
}

.ai-assistant-panel-app__body {
  flex: 1;
  overflow: auto;
  padding: var(--dimension-4);
}
</style>
