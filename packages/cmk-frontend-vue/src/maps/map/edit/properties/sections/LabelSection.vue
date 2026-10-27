<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The caption drawn next to the object. Background, border and length limit are
behind a disclosure: most maps never touch them.
-->
<script setup lang="ts">
import { CmkCollapsibleTitle } from 'cmk-ui-library/components/CmkCollapsible'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { ref, watch } from 'vue'

import PropertyInline from '@/maps/map/edit/properties/PropertyInline.vue'
import PropertyInlineInput from '@/maps/map/edit/properties/PropertyInlineInput.vue'
import PropertyRow from '@/maps/map/edit/properties/PropertyRow.vue'
import PropertySection from '@/maps/map/edit/properties/PropertySection.vue'
import type { ObjectForm } from '@/maps/map/edit/properties/objectForm'
import MapsColorInput from '@/maps/shared/components/MapsColorInput.vue'
import type { MapElement } from '@/maps/types/api'

const props = defineProps<{ object: MapElement }>()

const form = defineModel<ObjectForm>('form', { required: true })

const { _t } = usei18n()

const showAdvanced = ref(false)
// Another object starts over with the disclosure closed.
watch(
  () => props.object.id,
  () => (showAdvanced.value = false)
)
</script>

<template>
  <PropertySection :title="_t('Label')" :empty="!form.label.show">
    <template #title-control>
      <CmkCheckbox v-model="form.label.show" :aria-label="_t('Show label')" />
    </template>

    <PropertyRow
      v-if="object.type !== 'textbox'"
      v-slot="{ id }"
      labels-control
      :label="_t('Text')"
    >
      <CmkInput
        :id="id"
        v-model="form.label.text"
        :placeholder="_t('(auto from object)')"
        field-size="fill"
      />
    </PropertyRow>
    <PropertyRow v-slot="{ id }" labels-control :label="_t('Font size')">
      <CmkInput :id="id" v-model="form.label.size" type="number" min="8" max="72" unit="px" />
    </PropertyRow>
    <PropertyRow v-slot="{ id, label }" labels-control :label="_t('Color')">
      <MapsColorInput
        v-model="form.label.color"
        :label="label"
        :input-id="id"
        default-color="#ffffff"
      />
    </PropertyRow>
    <PropertyRow :label="_t('Offset')">
      <PropertyInline>
        <PropertyInlineInput v-model="form.label.x" :label="_t('X')" unit="px" />
        <PropertyInlineInput v-model="form.label.y" :label="_t('Y')" unit="px" />
      </PropertyInline>
    </PropertyRow>

    <CmkCollapsibleTitle
      :title="_t('Background & border')"
      :open="showAdvanced"
      @toggle-open="showAdvanced = !showAdvanced"
    />
    <template v-if="showAdvanced">
      <PropertyRow v-slot="{ id, label }" labels-control :label="_t('Background')">
        <MapsColorInput
          v-model="form.label.background"
          :label="label"
          :input-id="id"
          :enable-label="_t('Use color')"
          none-value="transparent"
          default-color="#000000"
        />
      </PropertyRow>
      <PropertyRow v-slot="{ id, label }" labels-control :label="_t('Border color')">
        <MapsColorInput
          v-model="form.label_border"
          :label="label"
          :input-id="id"
          :enable-label="_t('Use color')"
          default-color="#e5e5e5"
        />
      </PropertyRow>
      <PropertyRow v-slot="{ id }" labels-control :label="_t('Max length')">
        <CmkInput
          :id="id"
          v-model="form.label_maxlen"
          type="number"
          min="0"
          :placeholder="_t('no limit')"
        />
      </PropertyRow>
    </template>
  </PropertySection>
</template>
