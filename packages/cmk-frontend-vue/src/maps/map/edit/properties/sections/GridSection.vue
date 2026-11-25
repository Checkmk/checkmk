<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
How a grid lays out its objects, from its own position: how many per row, how
far apart, in which order.
-->
<script setup lang="ts">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import PropertyRow from '@/maps/map/edit/properties/PropertyRow.vue'
import PropertySection from '@/maps/map/edit/properties/PropertySection.vue'
import {
  type GridOrderChoice,
  type ObjectForm,
  gridOrderChoice,
  gridSortAndOrder,
  isGridOrderChoice
} from '@/maps/map/edit/properties/objectForm'

const form = defineModel<ObjectForm>('form', { required: true })

const { _t } = usei18n()

const orderOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: 'name', title: _t('Name') },
    { name: 'state', title: _t('State, worst first') },
    { name: 'state_desc', title: _t('State, best first') }
  ]
}))

const order = computed<GridOrderChoice>({
  get: () => gridOrderChoice(form.value),
  set: (value) => Object.assign(form.value, gridSortAndOrder(value))
})

function pickOrder(value: string | null): void {
  order.value = value !== null && isGridOrderChoice(value) ? value : 'name'
}
</script>

<template>
  <PropertySection :title="_t('Grid')">
    <PropertyRow v-slot="{ id }" labels-control :label="_t('Objects per row')">
      <CmkInput :id="id" v-model="form.grid_per_row" type="number" />
    </PropertyRow>
    <PropertyRow v-slot="{ id }" labels-control :label="_t('Spacing X')">
      <CmkInput :id="id" v-model="form.grid_offset_x" type="number" unit="px" />
    </PropertyRow>
    <PropertyRow v-slot="{ id }" labels-control :label="_t('Spacing Y')">
      <CmkInput :id="id" v-model="form.grid_offset_y" type="number" unit="px" />
    </PropertyRow>
    <PropertyRow :label="_t('Order')">
      <CmkDropdown
        floating
        :model-value="order"
        :options="orderOptions"
        :label="_t('Order')"
        width="fill"
        @update:model-value="pickOrder"
      />
    </PropertyRow>
    <p class="maps-grid-section__note">
      {{
        _t(
          'Label and appearance apply to each object of the grid. Showing the label widens the spacing for it; a label wider than spacing X is cut off, except on a NagVis-classic map. Drag an object out of the grid, or use "Pin out of the grid" in its context menu, to place it on its own.'
        )
      }}
    </p>
  </PropertySection>
</template>

<style scoped>
.maps-grid-section__note {
  margin: 0;
  color: var(--font-color-dimmed);
  font-size: var(--font-size-small);
}
</style>
