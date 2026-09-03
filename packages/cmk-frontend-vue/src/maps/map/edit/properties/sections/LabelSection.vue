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
  <PropertySection :title="_t('Label')">
    <PropertyRow :label="_t('Show label')">
      <CmkCheckbox v-model="form.label.show" />
    </PropertyRow>

    <div :class="{ 'maps-label-section--off': !form.label.show }">
      <div class="maps-label-section__rows">
        <PropertyRow v-if="object.type !== 'textbox'" :label="_t('Label text')">
          <CmkInput
            v-model="form.label.text"
            :placeholder="_t('(auto from object)')"
            field-size="fill"
          />
        </PropertyRow>
        <PropertyRow :label="_t('Size')">
          <CmkInput v-model="form.label.size" type="number" min="8" max="72" />
        </PropertyRow>
        <PropertyRow :label="_t('Color')">
          <MapsColorInput v-model="form.label.color" default-color="#ffffff" />
        </PropertyRow>
        <PropertyRow :label="_t('Offset X')">
          <CmkInput v-model="form.label.x" type="number" />
        </PropertyRow>
        <PropertyRow :label="_t('Offset Y')">
          <CmkInput v-model="form.label.y" type="number" />
        </PropertyRow>

        <CmkCollapsibleTitle
          :title="_t('Background & border')"
          :open="showAdvanced"
          @toggle-open="showAdvanced = !showAdvanced"
        />
        <template v-if="showAdvanced">
          <PropertyRow :label="_t('Background')">
            <MapsColorInput
              v-model="form.label.background"
              :enable-label="_t('Use color')"
              none-value="transparent"
              default-color="#000000"
            />
          </PropertyRow>
          <PropertyRow :label="_t('Border color')">
            <MapsColorInput
              v-model="form.label_border"
              :enable-label="_t('Use color')"
              default-color="#e5e5e5"
            />
          </PropertyRow>
          <PropertyRow :label="_t('Max length')">
            <CmkInput
              v-model="form.label_maxlen"
              type="number"
              min="0"
              :placeholder="_t('no limit')"
            />
          </PropertyRow>
        </template>
      </div>
    </div>
  </PropertySection>
</template>

<style scoped>
/* A hidden label still has settings, but changing them has no visible effect
   until it is shown again. */
.maps-label-section--off {
  opacity: 0.5;
}

.maps-label-section__rows {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}
</style>
