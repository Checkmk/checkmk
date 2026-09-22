<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import type { PresentationTheme, ShapeElement } from '@/maps/types/api'

import { fieldNumber } from '../../elements'
import { themeTokens } from '../../themes'
import ColorField from '../ColorField.vue'

const { _t } = usei18n()

const props = defineProps<{ element: ShapeElement; theme: PresentationTheme }>()
const emit = defineEmits<{ patch: [Record<string, unknown>] }>()

function patch(key: 'stroke_width' | 'corner_radius', value: unknown): void {
  const n = fieldNumber(value)
  if (n !== null) {
    emit('patch', { [key]: n })
  }
}

const tokens = computed(() => themeTokens(props.theme))

const isConnector = computed(
  () => props.element.shape === 'line' || props.element.shape === 'arrow'
)

// A dropdown rather than a toggle group: the inspector column is 280px and
// CmkToggleButtonGroup is the form-scale control (150px per option), so three
// options wrap onto two rows.
const dashOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: 'solid', title: _t('Solid') },
    { name: 'dashed', title: _t('Dashed') },
    { name: 'dotted', title: _t('Dotted') }
  ]
}))
</script>

<template>
  <section class="maps-inspector-appearance-section">
    <h3 class="maps-section-title">{{ _t('Appearance') }}</h3>
    <div class="maps-inspector-appearance-section__row">
      <div v-if="!isConnector" class="maps-inspector-appearance-section__field">
        <span class="maps-cap">{{ _t('Fill') }}</span>
        <ColorField
          :label="_t('Fill')"
          :value="element.fill"
          :default-color="tokens['--pres-shape-fill']"
          @set="emit('patch', { fill: $event })"
        />
      </div>
      <div class="maps-inspector-appearance-section__field">
        <span class="maps-cap">{{ _t('Stroke') }}</span>
        <ColorField
          :label="_t('Stroke')"
          :value="element.stroke"
          :default-color="tokens['--pres-shape-stroke']"
          @set="emit('patch', { stroke: $event })"
        />
      </div>
      <label class="maps-inspector-appearance-section__num">
        <span class="maps-cap">{{ _t('Width') }}</span>
        <CmkInput
          type="number"
          :model-value="element.stroke_width"
          min="0"
          max="64"
          @update:model-value="patch('stroke_width', $event)"
        />
      </label>
    </div>
    <div class="maps-inspector-appearance-section__row">
      <div v-if="!element.flow" class="maps-inspector-appearance-section__field">
        <span class="maps-cap">{{ _t('Stroke style') }}</span>
        <CmkDropdown
          :model-value="element.dash"
          :options="dashOptions"
          :label="_t('Stroke style')"
          width="fill"
          @update:model-value="emit('patch', { dash: $event })"
        />
      </div>
      <div v-else class="maps-inspector-appearance-section__field">
        <span class="maps-cap">{{ _t('Stroke style') }}</span>
        <span class="maps-inspector-appearance-section__note">{{
          _t('Flow animation overrides the stroke style')
        }}</span>
      </div>
      <label v-if="element.shape === 'rect'" class="maps-inspector-appearance-section__num">
        <span class="maps-cap">{{ _t('Radius') }}</span>
        <CmkInput
          type="number"
          :model-value="element.corner_radius"
          min="0"
          @update:model-value="patch('corner_radius', $event)"
        />
      </label>
    </div>
  </section>
</template>

<style scoped>
.maps-inspector-appearance-section {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}

.maps-inspector-appearance-section__row {
  display: flex;
  align-items: flex-end;
  gap: var(--dimension-4);
}

.maps-inspector-appearance-section__field {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
  min-width: 0;
}

.maps-inspector-appearance-section__num {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
  width: 76px;
}

.maps-inspector-appearance-section__note {
  font-size: var(--font-size-normal);
  color: var(--font-color-dimmed);
}
</style>
