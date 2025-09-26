<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import CmkIconButton from '@/components/CmkIconButton.vue'

import DashboardContent from '@/dashboard-wip/components/DashboardContent/DashboardContent.vue'
import type { ContentProps } from '@/dashboard-wip/components/DashboardContent/types'

import type { ResizeDirection } from './helpers/resizeHelper.ts'
import { ANCHOR_POSITION, type DimensionModes, SIZING_MODE } from './types'

const { _t } = usei18n()

const props = defineProps<{
  debug?: boolean
  isEditing: boolean
  contentProps: ContentProps
  isResizable: boolean
  dimensions: { width: number; height: number }
  position: { left: number; top: number }
  zIndex: number
  anchorPosition: ANCHOR_POSITION
  dimensionModes: DimensionModes
  handleDrag: (e: PointerEvent) => void
  handleResize: (e: PointerEvent, direction: ResizeDirection) => void
}>()

const emit = defineEmits<{
  (e: 'click:edit'): void
  (e: 'click:clone'): void
  (e: 'click:delete'): void
  (e: 'toggle:sizing', dimension: 'width' | 'height'): void
  (e: 'update:anchorPosition', position: ANCHOR_POSITION): void
}>()

const containerStyle = computed(() => ({
  top: `${props.position?.top || 0}px`,
  left: `${props.position?.left || 0}px`,
  width: `${props.dimensions?.width || 100}px`,
  height: `${props.dimensions?.height || 100}px`
}))

const anchorBg = (pos: string) =>
  props.anchorPosition === pos
    ? 'var(--color-corporate-green-50, #1db954)'
    : 'var(--ux-theme-5, rgb(255,255,255,0.06))'

const getSizingText = (mode: SIZING_MODE | undefined, dimension: 'width' | 'height'): string => {
  if (!mode) {
    return `manual ${dimension}`
  }
  switch (mode) {
    case SIZING_MODE.MAX:
      return `max ${dimension}`
    case SIZING_MODE.GROW:
      return `auto ${dimension}`
    case SIZING_MODE.MANUAL:
    default:
      return `manual ${dimension}`
  }
}

const anchorCorners = [
  { key: 'tl', pos: ANCHOR_POSITION.TOP_LEFT },
  { key: 'tr', pos: ANCHOR_POSITION.TOP_RIGHT },
  { key: 'bl', pos: ANCHOR_POSITION.BOTTOM_LEFT },
  { key: 'br', pos: ANCHOR_POSITION.BOTTOM_RIGHT }
]

function onAnchorSelect(pos: ANCHOR_POSITION) {
  emit('update:anchorPosition', pos)
}
</script>

<template>
  <div
    :id="`db-relative-grid-frame-${contentProps.widget_id}`"
    class="db-relative-grid-frame"
    :style="{ ...containerStyle }"
  >
    <div :style="{ position: 'relative', height: '100%', width: '100%', zIndex: zIndex }">
      <DashboardContent v-bind="contentProps" />

      <div
        v-if="props.isEditing"
        :id="`dashlet_controls_${contentProps!.widget_id}`"
        class="controls"
        @pointerdown="handleDrag"
      >
        <!-- Resize handles -->
        <div
          v-if="isResizable && props.dimensionModes.width === SIZING_MODE.MANUAL"
          class="resize-handle resize-left"
          @pointerdown.stop.prevent="(e) => handleResize(e, 'left')"
        ></div>
        <div
          v-if="isResizable && props.dimensionModes.width === SIZING_MODE.MANUAL"
          class="resize-handle resize-right"
          @pointerdown.stop.prevent="(e) => handleResize(e, 'right')"
        ></div>
        <div
          v-if="isResizable && props.dimensionModes.height === SIZING_MODE.MANUAL"
          class="resize-handle resize-top"
          @pointerdown.stop.prevent="(e) => handleResize(e, 'top')"
        ></div>
        <div
          v-if="isResizable && props.dimensionModes.height === SIZING_MODE.MANUAL"
          class="resize-handle resize-bottom"
          @pointerdown.stop.prevent="(e) => handleResize(e, 'bottom')"
        ></div>

        <!-- Anchors -->
        <template v-for="corner in anchorCorners" :key="corner.key">
          <div class="anchor-slot" :class="`anchor--${corner.key}`">
            <div
              class="anchor-icon"
              :style="{ background: anchorBg(corner.pos) }"
              aria-hidden="true"
              @pointerdown.stop.prevent="onAnchorSelect(corner.pos)"
            />
            <div v-if="props.anchorPosition === corner.pos" class="anchor-label anchor-label-pos">
              {{ _t('Anchor') }}
            </div>
          </div>
        </template>

        <!-- Centered edit controls -->
        <div class="db-centered-edit-controls">
          <!-- left column: sizing buttons -->
          <div v-if="isResizable" class="db-sizing-controls">
            <button
              class="db-centered-edit-controls-button sizing-button"
              :title="_t('Toggle sizing for width')"
              @click.stop="emit('toggle:sizing', 'width')"
            >
              {{ getSizingText(props.dimensionModes.width, 'width') }}
            </button>

            <button
              class="db-centered-edit-controls-button sizing-button"
              :title="_t('Toggle sizing for height')"
              @click.stop="emit('toggle:sizing', 'height')"
            >
              {{ getSizingText(props.dimensionModes.height, 'height') }}
            </button>
          </div>

          <!-- right row: icon buttons -->
          <div class="db-icon-controls">
            <CmkIconButton
              class="db-centered-edit-controls-button"
              name="widget_delete"
              size="xxlarge"
              @click="emit('click:delete')"
            />
            <CmkIconButton
              class="db-centered-edit-controls-button"
              name="widget_clone"
              size="xxlarge"
              @click="emit('click:clone')"
            />
            <CmkIconButton
              class="db-centered-edit-controls-button"
              name="widget_edit"
              size="xxlarge"
              @click="emit('click:edit')"
            />
          </div>
        </div>

        <!-- Debug info -->
        <div v-if="debug" class="debug-container">
          {{ dimensions.width }} x {{ dimensions.height }} | {{ position.left }},{{ position.top }}
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Not applying the dimension variables because this is unique to the relative grid implementation */

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.db-relative-grid-frame {
  --anchor-size: 16px;

  position: absolute;
  display: flex;
  flex-direction: column;
  margin: 0;
  padding: var(--dimension-3);
  box-sizing: border-box;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.controls {
  position: absolute;
  top: 0;
  left: 0;
  isolation: isolate;
  width: 100%;
  height: 100%;
  z-index: 1000;
  cursor: auto;
  background-color: rgb(from var(--ux-theme-4) r g b / 80%);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.resize-handle {
  position: absolute;
  z-index: 1100;
  background-color: rgb(from var(--color-corporate-green-80) r g b / 25%);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.resize-left {
  top: 0;
  left: 0;
  width: 6px;
  height: 100%;
  border-left: 2px dashed var(--color-corporate-green-50);
  cursor: ew-resize;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.resize-right {
  top: 0;
  right: 0;
  width: 6px;
  height: 100%;
  border-right: 2px dashed var(--color-corporate-green-50);
  cursor: ew-resize;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.resize-top {
  top: 0;
  left: 0;
  width: 100%;
  height: 6px;
  border-top: 2px dashed var(--color-corporate-green-50);
  cursor: ns-resize;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.resize-bottom {
  bottom: 0;
  left: 0;
  width: 100%;
  height: 6px;
  border-bottom: 2px dashed var(--color-corporate-green-50);
  cursor: ns-resize;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.anchor-slot {
  position: absolute;
  z-index: 1101;
  pointer-events: none; /* prevents stray pointer hits on the slot itself */
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.anchor-icon {
  width: var(--anchor-size);
  height: var(--anchor-size);
  border: 1px solid rgb(from var(--black) r g b / 15%);
  pointer-events: auto; /* re-enable on the actual target */
  cursor: pointer;
  clip-path: polygon(0 0, 100% 0, 0 100%); /* default TL shape */
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.anchor-label {
  position: absolute;
  font-size: 12px;
  font-weight: 500;
  color: var(--color-corporate-green-50);
  white-space: nowrap;
  pointer-events: none;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.anchor--tl {
  top: 6px;
  left: 6px;

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  & .anchor-icon {
    clip-path: polygon(0 0, 100% 0, 0 100%);
  }

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  & .anchor-label-pos {
    top: 10px;
    left: 24px;
  }
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.anchor--tr {
  top: 6px;
  right: 6px;

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  & .anchor-icon {
    clip-path: polygon(100% 0, 100% 100%, 0 0);
  }

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  & .anchor-label-pos {
    top: 10px;
    right: 24px;
  }
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.anchor--bl {
  bottom: 6px;
  left: 6px;

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  & .anchor-icon {
    clip-path: polygon(0 100%, 100% 100%, 0 0);
  }

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  & .anchor-label-pos {
    bottom: 10px;
    left: 24px;
  }
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.anchor--br {
  bottom: 6px;
  right: 6px;

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  & .anchor-icon {
    clip-path: polygon(100% 100%, 0 100%, 100% 0);
  }

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  & .anchor-label-pos {
    bottom: 10px;
    right: 24px;
  }
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.anchor-icon:hover {
  filter: brightness(1.15);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.db-centered-edit-controls {
  position: absolute;
  top: 50%;
  left: 50%;
  display: flex;
  flex-direction: column;
  gap: 4px;
  transform: translate(-50%, -50%);
  z-index: 1200;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.db-sizing-controls {
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: center;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.db-icon-controls {
  display: flex;
  flex-direction: row;
  gap: 8px;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.db-centered-edit-controls-button {
  padding: 8px 10px;
  filter: brightness(0) saturate(100%) invert(100%) brightness(70%);
  transition: filter 200ms ease;
  border: none;
  background: transparent;
  color: inherit;
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
  border-radius: 6px;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.db-centered-edit-controls-button:hover {
  filter: brightness(0) saturate(100%) invert(100%) brightness(100%);
  background-color: rgb(from var(--white) r g b / 3%);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.sizing-button {
  min-width: 100px;
  text-transform: none;
  letter-spacing: 0.2px;
  background: rgb(from var(--white) r g b / 20%);
  border: 1px solid rgb(from var(--white) r g b / 30%);
  border-radius: 6px;
  color: var(--font-color);
  font-size: 13px;
  font-weight: 500;
  text-align: center;
  padding: 6px 12px;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.sizing-button:hover {
  background: rgb(from var(--white) r g b / 20%);
  border-color: rgb(from var(--white) r g b / 30%);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.debug-container {
  position: absolute;
  bottom: 4px;
  left: 4px;
  font-size: 10px;
  color: var(--font-color);
  padding: 2px 4px;
  border-radius: 3px;
  pointer-events: none;
  z-index: 2000;
}
</style>
