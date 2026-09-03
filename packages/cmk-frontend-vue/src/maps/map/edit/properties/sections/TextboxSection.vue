<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
A textbox has no monitoring object behind it — only the text it shows and the
box it is drawn in.
-->
<script setup lang="ts">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import PropertyRow from '@/maps/map/edit/properties/PropertyRow.vue'
import PropertySection from '@/maps/map/edit/properties/PropertySection.vue'
import type { ObjectForm } from '@/maps/map/edit/properties/objectForm'
import MapsColorInput from '@/maps/shared/components/MapsColorInput.vue'
import MapsTextArea from '@/maps/shared/components/MapsTextArea.vue'

const form = defineModel<ObjectForm>('form', { required: true })

const { _t } = usei18n()

// A dropdown rather than a toggle group: the card's control column is ~320px
// and CmkToggleButtonGroup is the form-scale control (150px per option), so
// three options wrap onto two rows.
const alignOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: 'left', title: _t('Left') },
    { name: 'center', title: _t('Center') },
    { name: 'right', title: _t('Right') }
  ]
}))
</script>

<template>
  <PropertySection :title="_t('Content')">
    <MapsTextArea v-model="form.label.text" :placeholder="_t('Text content…')" />
    <PropertyRow :label="_t('Alignment')">
      <CmkDropdown
        floating
        :model-value="form.label.align ?? 'left'"
        :options="alignOptions"
        :label="_t('Alignment')"
        width="fill"
        @update:model-value="form.label.align = ($event ?? 'left') as 'left' | 'center' | 'right'"
      />
    </PropertyRow>
    <PropertyRow :label="_t('Width')">
      <CmkInput v-model="form.textbox_width" type="number" :placeholder="_t('auto')" />
    </PropertyRow>
    <PropertyRow :label="_t('Height')">
      <CmkInput v-model="form.textbox_height" type="number" :placeholder="_t('auto')" />
    </PropertyRow>
    <PropertyRow :label="_t('Background')">
      <MapsColorInput
        v-model="form.textbox_background"
        :enable-label="_t('Use color')"
        default-color="#1a1a2e"
      />
    </PropertyRow>
    <PropertyRow :label="_t('Border color')">
      <MapsColorInput
        v-model="form.textbox_border"
        :enable-label="_t('Use color')"
        default-color="#e5e5e5"
      />
    </PropertyRow>
  </PropertySection>
</template>
