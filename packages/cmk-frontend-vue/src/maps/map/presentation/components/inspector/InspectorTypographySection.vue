<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkCatalogPanel from 'cmk-ui-library/components/CmkCatalogPanel.vue'
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import CmkToggleButtonGroup from 'cmk-ui-library/components/CmkToggleButtonGroup.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import EditField from '@/maps/map/edit/components/EditField.vue'
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
</script>

<template>
  <CmkCatalogPanel :title="_t('Typography')">
    <div class="maps-inspector-typography-section">
      <EditField class="maps-inspector-typography-section__field" :label="_t('Font')">
        <CmkDropdown
          :model-value="element.font_family ?? ''"
          :options="fontOptions"
          :width="'fill'"
          :label="_t('Font')"
          @update:model-value="emit('patch', { font_family: $event || null })"
        />
      </EditField>
      <div class="maps-inspector-typography-section__row">
        <EditField
          v-slot="{ id }"
          class="maps-inspector-typography-section__num"
          labels-control
          :label="_t('Size')"
        >
          <CmkInput
            :id="id"
            type="number"
            unit="px"
            :model-value="element.font_size"
            min="4"
            max="512"
            @update:model-value="patch('font_size', $event)"
          />
        </EditField>
        <EditField class="maps-inspector-typography-section__field" :label="_t('Style')">
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
        </EditField>
      </div>
      <EditField class="maps-inspector-typography-section__field" :label="_t('Align')">
        <CmkToggleButtonGroup
          :model-value="element.text_align"
          :options="alignOptions"
          size="small"
          @update:model-value="emit('patch', { text_align: $event })"
        />
      </EditField>
      <div class="maps-inspector-typography-section__row">
        <EditField class="maps-inspector-typography-section__field" :label="_t('Color')">
          <ColorField
            :label="_t('Color')"
            :default-color="tokens['--pres-fg']"
            :value="element.color"
            @set="emit('patch', { color: $event })"
          />
        </EditField>
        <EditField class="maps-inspector-typography-section__field" :label="_t('Background')">
          <ColorField
            :label="_t('Background')"
            :value="element.background"
            @set="emit('patch', { background: $event })"
          />
        </EditField>
      </div>
    </div>
  </CmkCatalogPanel>
</template>

<style scoped>
.maps-inspector-typography-section {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
  padding: var(--dimension-4) 0;
}

.maps-inspector-typography-section__row {
  display: flex;
  align-items: flex-start;
  gap: var(--dimension-4);
}

.maps-inspector-typography-section__field,
.maps-inspector-typography-section__num {
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
  margin: 0;
  border: 1px solid var(--default-form-element-border-color);
  border-radius: var(--border-radius);
  background: transparent;
  color: var(--font-color);
  cursor: pointer;
  font-weight: var(--font-weight-bold);
}

.maps-inspector-typography-section__toggle--i {
  font-style: italic;
}

.maps-inspector-typography-section__toggle--on {
  background: color-mix(in srgb, var(--interactive-accent) 20%, transparent);
  border-color: var(--interactive-accent);
}
</style>
