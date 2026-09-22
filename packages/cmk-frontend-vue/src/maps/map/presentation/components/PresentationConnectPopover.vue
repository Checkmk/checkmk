<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The binding form for the slot the connect walkthrough is currently on. It
follows the slot around the slide (``useConnectWalkthrough`` places it), so the
element being connected stays in view while it is being filled in.

Binding a host does not advance on its own: the slot stays current so a service
and a label can still be picked. Moving on is always explicit.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import CmkIconButton from 'cmk-ui-library/components/CmkIconButton.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

import type { DataElement } from '@/maps/types/api'

import type { BindableElement } from '../binding'
import PresentationBindingForm from './PresentationBindingForm.vue'
import PresentationGadgetMetricField from './PresentationGadgetMetricField.vue'
import PresentationPanel from './PresentationPanel.vue'

const { _t } = usei18n()

defineProps<{
  element: BindableElement
  /** The map's default connection, for elements that carry none of their own. */
  connectionId: string
  title: string
  bound: boolean
  /** Set while the current slot is a gadget that still needs a metric. */
  metricElement: DataElement | null
  /** How many slots are still unbound -- none left turns Next into Finish. */
  remaining: number
  position: { left: string; top: string } | null
}>()

const emit = defineEmits<{
  patch: [patch: Record<string, unknown>]
  next: []
  done: []
}>()
</script>

<template>
  <!-- Hidden rather than absent until measured: the form's height decides where
       it can sit, and a flash at the top-left corner would be worse. -->
  <PresentationPanel
    raised
    class="maps-presentation-connect-popover"
    :style="position ?? { visibility: 'hidden', left: '0px', top: '0px' }"
    @pointerdown.stop
  >
    <div class="maps-presentation-connect-popover__head">
      <CmkIcon v-if="bound" name="checkmark" size="small" :title="_t('Connected')" />
      <span class="maps-presentation-connect-popover__title">{{ title }}</span>
      <CmkIconButton
        name="close"
        size="small"
        :title="_t('Done')"
        :aria-label="_t('Done')"
        @click="emit('done')"
      />
    </div>
    <div class="maps-presentation-connect-popover__body">
      <PresentationBindingForm
        :element="element"
        :connection-id="connectionId"
        @patch="emit('patch', $event)"
      >
        <template #after-binding>
          <PresentationGadgetMetricField
            v-if="metricElement"
            :element="metricElement"
            :connection-id="connectionId"
            @patch="emit('patch', $event)"
          />
        </template>
      </PresentationBindingForm>
    </div>
    <div class="maps-presentation-connect-popover__foot">
      <CmkButton v-if="!bound" variant="optional" size="small" @click="emit('next')">
        {{ _t('Skip') }}
      </CmkButton>
      <CmkButton v-else variant="primary" @click="emit('next')">
        {{ remaining ? _t('Next') : _t('Finish') }}
      </CmkButton>
    </div>
  </PresentationPanel>
</template>

<style scoped>
.maps-presentation-connect-popover {
  position: absolute;
  z-index: 7;
  width: 264px;
  color: var(--font-color);
}

.maps-presentation-connect-popover__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--dimension-4);
  padding: 8px 12px;
  font-weight: var(--font-weight-bold);
  font-size: var(--font-size-normal);
  border-bottom: 1px solid var(--default-border-color);
}

.maps-presentation-connect-popover__title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.maps-presentation-connect-popover__body {
  padding: 10px 12px;
}

.maps-presentation-connect-popover__foot {
  display: flex;
  justify-content: flex-end;
  padding: 8px 12px;
  border-top: 1px solid var(--default-border-color);
}
</style>
