<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Where the object sits: a coordinate on a canvas map, a latitude and longitude
on a geo map, and how it stacks against its neighbours.
-->
<script setup lang="ts">
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import PropertyRow from '@/maps/map/edit/properties/PropertyRow.vue'
import PropertySection from '@/maps/map/edit/properties/PropertySection.vue'
import type { ObjectForm } from '@/maps/map/edit/properties/objectForm'
import type { MapViewType } from '@/maps/types/api'

const props = defineProps<{ mapType: MapViewType | undefined }>()

const form = defineModel<ObjectForm>('form', { required: true })

const { _t } = usei18n()

const isGeo = computed(() => props.mapType === 'worldmap')
</script>

<template>
  <PropertySection :title="_t('Position')">
    <template v-if="isGeo">
      <PropertyRow :label="_t('Lat')">
        <CmkInput v-model="form.lat" type="number" step="any" />
      </PropertyRow>
      <PropertyRow :label="_t('Lng')">
        <CmkInput v-model="form.lng" type="number" step="any" />
      </PropertyRow>
    </template>
    <template v-else>
      <PropertyRow :label="_t('X')">
        <CmkInput v-model="form.x" type="number" min="0" max="10000" />
      </PropertyRow>
      <PropertyRow :label="_t('Y')">
        <CmkInput v-model="form.y" type="number" min="0" max="10000" />
      </PropertyRow>
    </template>
    <PropertyRow :label="_t('Z')">
      <CmkInput v-model="form.z" type="number" min="1" max="999" />
    </PropertyRow>
  </PropertySection>
</template>
