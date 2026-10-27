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
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import PropertyInline from '@/maps/map/edit/properties/PropertyInline.vue'
import PropertyInlineInput from '@/maps/map/edit/properties/PropertyInlineInput.vue'
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
    <PropertyInline :label="_t('Position')">
      <template v-if="isGeo">
        <PropertyInlineInput v-model="form.lat" :label="_t('Lat')" unit="°" wide />
        <PropertyInlineInput v-model="form.lng" :label="_t('Lng')" unit="°" wide />
      </template>
      <template v-else>
        <PropertyInlineInput v-model="form.x" :label="_t('X')" unit="px" min="0" max="10000" />
        <PropertyInlineInput v-model="form.y" :label="_t('Y')" unit="px" min="0" max="10000" />
      </template>
      <PropertyInlineInput v-model="form.z" :label="_t('Z')" min="1" max="999" />
    </PropertyInline>
  </PropertySection>
</template>
