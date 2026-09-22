<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import type { PresentationTheme, TextElement } from '@/maps/types/api'

import { fieldNumber } from '../../elements'
import { PRESENTATION_FONTS } from '../../fonts'
import { themeTokens } from '../../themes'
import ColorField from '../ColorField.vue'

const { _t } = usei18n()

const props = defineProps<{ element: TextElement; theme: PresentationTheme }>()
const emit = defineEmits<{ patch: [Record<string, unknown>] }>()

function patch(key: 'font_size', value: unknown): void {
  const n = fieldNumber(value)
  if (n !== null) {
    emit('patch', { [key]: n })
  }
}

const tokens = computed(() => themeTokens(props.theme))

const fontOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: PRESENTATION_FONTS.map((f) => ({
    name: f.stack ?? '',
    title: f.stack === null ? _t('Theme default') : untranslated(f.title)
  }))
}))

const alignOptions = computed(() => [
  { label: _t('Left'), value: 'left' },
  { label: _t('Center'), value: 'center' },
  { label: _t('Right'), value: 'right' }
])

// [x1, x2] per text line (y stepped in the template) — drawn as a left/center/
// right-justified stack of rules, the universal text-alignment glyph.
const alignLines: Record<string, [number, number][]> = {
  left: [
    [4, 20],
    [4, 14],
    [4, 20],
    [4, 14]
  ],
  center: [
    [4, 20],
    [7, 17],
    [4, 20],
    [7, 17]
  ],
  right: [
    [4, 20],
    [10, 20],
    [4, 20],
    [10, 20]
  ]
}
</script>

<template>
  <section class="maps-inspector-typography-section">
    <h3 class="maps-section-title">{{ _t('Typography') }}</h3>
    <div class="maps-inspector-typography-section__field">
      <span class="maps-cap">{{ _t('Font') }}</span>
      <CmkDropdown
        :model-value="element.font_family ?? ''"
        :options="fontOptions"
        :width="'fill'"
        :label="_t('Font')"
        @update:model-value="emit('patch', { font_family: $event || null })"
      />
    </div>
    <div class="maps-inspector-typography-section__row">
      <label class="maps-inspector-typography-section__num">
        <span class="maps-cap">{{ _t('Size') }}</span>
        <CmkInput
          type="number"
          :model-value="element.font_size"
          min="4"
          max="512"
          @update:model-value="patch('font_size', $event)"
        />
      </label>
      <div class="maps-inspector-typography-section__field">
        <span class="maps-cap">{{ _t('Style') }}</span>
        <div class="maps-inspector-typography-section__toggles">
          <button
            class="maps-inspector-typography-section__toggle"
            :class="{
              'maps-inspector-typography-section__toggle--on': element.font_weight === 'bold'
            }"
            :title="_t('Bold')"
            @click="
              emit('patch', { font_weight: element.font_weight === 'bold' ? 'normal' : 'bold' })
            "
          >
            {{ _t('B') }}
          </button>
          <button
            class="maps-inspector-typography-section__toggle maps-inspector-typography-section__toggle--i"
            :class="{
              'maps-inspector-typography-section__toggle--on': element.font_style === 'italic'
            }"
            :title="_t('Italic')"
            @click="
              emit('patch', { font_style: element.font_style === 'italic' ? 'normal' : 'italic' })
            "
          >
            {{ _t('I') }}
          </button>
        </div>
      </div>
    </div>
    <div class="maps-inspector-typography-section__field">
      <span class="maps-cap">{{ _t('Align') }}</span>
      <div class="maps-inspector-typography-section__toggles">
        <button
          v-for="opt in alignOptions"
          :key="opt.value"
          class="maps-inspector-typography-section__toggle"
          :class="{
            'maps-inspector-typography-section__toggle--on': element.text_align === opt.value
          }"
          :title="opt.label"
          :aria-label="opt.label"
          :aria-pressed="element.text_align === opt.value"
          @click="emit('patch', { text_align: opt.value })"
        >
          <svg
            class="maps-inspector-typography-section__toggle-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
          >
            <line
              v-for="(ln, i) in alignLines[opt.value]"
              :key="i"
              :x1="ln[0]"
              :y1="6 + i * 4"
              :x2="ln[1]"
              :y2="6 + i * 4"
            />
          </svg>
        </button>
      </div>
    </div>
    <div class="maps-inspector-typography-section__row">
      <div class="maps-inspector-typography-section__field">
        <span class="maps-cap">{{ _t('Color') }}</span>
        <ColorField
          :label="_t('Color')"
          :default-color="tokens['--pres-fg']"
          :value="element.color"
          @set="emit('patch', { color: $event })"
        />
      </div>
      <div class="maps-inspector-typography-section__field">
        <span class="maps-cap">{{ _t('Background') }}</span>
        <ColorField
          :label="_t('Background')"
          :value="element.background"
          @set="emit('patch', { background: $event })"
        />
      </div>
    </div>
  </section>
</template>

<style scoped>
.maps-inspector-typography-section {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}

.maps-inspector-typography-section__row {
  display: flex;
  align-items: flex-end;
  gap: var(--dimension-4);
}

.maps-inspector-typography-section__field,
.maps-inspector-typography-section__num {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
  min-width: 0;
  flex: 1;
}

.maps-inspector-typography-section__toggles {
  display: flex;
  gap: var(--dimension-3);
}

.maps-inspector-typography-section__toggle {
  width: 30px;
  height: 30px;
  border: 1px solid var(--default-form-element-border-color);
  border-radius: 6px;
  background: transparent;
  color: var(--font-color);
  cursor: pointer;
  font-weight: var(--font-weight-bold);
}

.maps-inspector-typography-section__toggle--i {
  font-style: italic;
}

.maps-inspector-typography-section__toggle-icon {
  width: 16px;
  height: 16px;
}

.maps-inspector-typography-section__toggle--on {
  background: color-mix(in srgb, var(--color-corporate-green-50) 20%, transparent);
  border-color: var(--color-corporate-green-50);
}
</style>
