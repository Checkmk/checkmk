<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkScrollContainer from 'cmk-ui-library/components/CmkScrollContainer.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import type { PresentationElement } from '@/maps/types/api'

import { type PresentationTemplate, presentationTemplates } from '../templates'
import PresentationSlidePreview from './PresentationSlidePreview.vue'

const { _t } = usei18n()

const emit = defineEmits<{ apply: [PresentationTemplate]; close: [] }>()

const templates = computed(() => presentationTemplates(_t))

// Build once per gallery open — element ids are freshly generated per build,
// so the preview must not rebuild on every render.
const previewCache = new Map<string, PresentationElement[]>()
function previewElements(t: PresentationTemplate): PresentationElement[] {
  let els = previewCache.get(t.id)
  if (!els) {
    els = t.build()
    previewCache.set(t.id, els)
  }
  return els
}
</script>

<template>
  <div class="maps-presentation-template-gallery" @pointerdown.stop>
    <div class="maps-presentation-template-gallery__card">
      <div class="maps-presentation-template-gallery__head">
        <div>
          <h2 class="maps-presentation-template-gallery__title">{{ _t('Start with a design') }}</h2>
          <p class="maps-presentation-template-gallery__sub">
            {{ _t('Pick a template, then connect your hosts and services — or start blank.') }}
          </p>
        </div>
        <button
          class="maps-presentation-template-gallery__x"
          :title="_t('Close')"
          @click="emit('close')"
        >
          {{ untranslated('×') }}
        </button>
      </div>
      <CmkScrollContainer class="maps-presentation-template-gallery__grid-wrap">
        <div class="maps-presentation-template-gallery__grid">
          <button
            v-for="t in templates"
            :key="t.id"
            class="maps-presentation-template-gallery__item"
            @click="emit('apply', t)"
          >
            <PresentationSlidePreview
              v-if="t.id !== 'blank'"
              :elements="previewElements(t)"
              :theme="t.theme"
            />
            <div v-else class="maps-presentation-template-gallery__blank">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M12 5v14M5 12h14" />
              </svg>
            </div>
            <span class="maps-presentation-template-gallery__item-title">{{ t.title }}</span>
            <span class="maps-presentation-template-gallery__item-desc">{{ t.description }}</span>
          </button>
        </div>
      </CmkScrollContainer>
    </div>
  </div>
</template>

<style scoped>
.maps-presentation-template-gallery {
  position: absolute;
  inset: 0;
  z-index: 8;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgb(0 0 0 / 45%);
}

.maps-presentation-template-gallery__card {
  display: flex;
  flex-direction: column;
  width: min(920px, calc(100% - 64px));
  max-height: calc(100% - 64px);
  border-radius: 14px;
  background: var(--ux-theme-3);
  border: 1px solid var(--default-border-color, rgb(255 255 255 / 8%));
  box-shadow: 0 24px 64px rgb(0 0 0 / 50%);
  color: var(--font-color);
}

.maps-presentation-template-gallery__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--dimension-5);
  padding: 20px 24px 12px;
}

.maps-presentation-template-gallery__title {
  margin: 0;
  font-size: 20px;
  font-weight: var(--font-weight-bold);
}

.maps-presentation-template-gallery__sub {
  margin: 4px 0 0;
  font-size: var(--font-size-large);
  color: var(--font-color-dimmed);
}

.maps-presentation-template-gallery__x {
  border: none;
  background: transparent;
  color: var(--font-color-dimmed);
  font-size: 22px;
  cursor: pointer;
}

.maps-presentation-template-gallery__x:hover {
  color: var(--font-color);
}

.maps-presentation-template-gallery__grid-wrap {
  flex: 1;
  min-height: 0;
}

.maps-presentation-template-gallery__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(264px, 1fr));
  gap: var(--dimension-6);
  padding: 12px 24px 24px;
}

.maps-presentation-template-gallery__item {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: var(--dimension-3);
  padding: var(--dimension-4);
  border: 1px solid var(--default-border-color, rgb(255 255 255 / 10%));
  border-radius: var(--dimension-5);
  background: transparent;
  color: inherit;
  cursor: pointer;
  text-align: left;
  transition:
    border-color 0.12s ease,
    transform 0.12s ease;
}

.maps-presentation-template-gallery__item:hover {
  border-color: var(--color-corporate-green-50);
  transform: translateY(-2px);
}

.maps-presentation-template-gallery__blank {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 139px;
  border: 1px dashed var(--default-border-color, rgb(255 255 255 / 18%));
  border-radius: var(--dimension-4);
  color: var(--font-color-dimmed);
}

.maps-presentation-template-gallery__blank svg {
  width: 36px;
  height: 36px;
}

.maps-presentation-template-gallery__item-title {
  margin-top: 6px;
  font-weight: var(--font-weight-bold);
  font-size: var(--font-size-large);
}

.maps-presentation-template-gallery__item-desc {
  font-size: var(--font-size-normal);
  color: var(--font-color-dimmed);
}
</style>
