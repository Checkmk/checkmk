<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkCatalogPanel from 'cmk-ui-library/components/CmkCatalogPanel.vue'
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import EditField from '@/maps/map/edit/components/EditField.vue'
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
  <CmkCatalogPanel :title="_t('Appearance')">
    <div class="maps-inspector-appearance-section">
      <div class="maps-inspector-appearance-section__row">
        <EditField
          v-if="!isConnector"
          class="maps-inspector-appearance-section__field"
          :label="_t('Fill')"
        >
          <ColorField
            :label="_t('Fill')"
            :value="element.fill"
            :default-color="tokens['--pres-shape-fill']"
            @set="emit('patch', { fill: $event })"
          />
        </EditField>
        <EditField class="maps-inspector-appearance-section__field" :label="_t('Stroke')">
          <ColorField
            :label="_t('Stroke')"
            :value="element.stroke"
            :default-color="tokens['--pres-shape-stroke']"
            @set="emit('patch', { stroke: $event })"
          />
        </EditField>
        <EditField
          v-slot="{ id }"
          class="maps-inspector-appearance-section__num"
          labels-control
          :label="_t('Width')"
        >
          <CmkInput
            :id="id"
            type="number"
            :model-value="element.stroke_width"
            min="0"
            max="64"
            @update:model-value="patch('stroke_width', $event)"
          />
        </EditField>
      </div>
      <div class="maps-inspector-appearance-section__row">
        <EditField
          v-if="!element.flow"
          class="maps-inspector-appearance-section__field"
          :label="_t('Stroke style')"
        >
          <CmkDropdown
            :model-value="element.dash"
            :options="dashOptions"
            :label="_t('Stroke style')"
            width="fill"
            @update:model-value="emit('patch', { dash: $event })"
          />
        </EditField>
        <EditField
          v-else
          class="maps-inspector-appearance-section__field"
          :label="_t('Stroke style')"
        >
          <span class="maps-inspector-appearance-section__note">{{
            _t('Flow animation overrides the stroke style')
          }}</span>
        </EditField>
        <EditField
          v-if="element.shape === 'rect'"
          v-slot="{ id }"
          class="maps-inspector-appearance-section__num"
          labels-control
          :label="_t('Radius')"
        >
          <CmkInput
            :id="id"
            type="number"
            :model-value="element.corner_radius"
            min="0"
            @update:model-value="patch('corner_radius', $event)"
          />
        </EditField>
      </div>
    </div>
  </CmkCatalogPanel>
</template>

<style scoped>
.maps-inspector-appearance-section {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
  padding: var(--dimension-4) 0;
}

.maps-inspector-appearance-section__row {
  display: flex;
  align-items: flex-end;
  gap: var(--dimension-4);
}

.maps-inspector-appearance-section__field {
  min-width: 0;
}

.maps-inspector-appearance-section__num {
  width: 76px;
}

.maps-inspector-appearance-section__note {
  font-size: var(--font-size-normal);
  color: var(--font-color-dimmed);
}
</style>
