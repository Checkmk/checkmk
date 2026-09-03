<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
A graph object can also show something the map does not draw itself: an image
or a page pulled in from a URL.
-->
<script setup lang="ts">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import PropertyRow from '@/maps/map/edit/properties/PropertyRow.vue'
import PropertySection from '@/maps/map/edit/properties/PropertySection.vue'
import type { ObjectForm } from '@/maps/map/edit/properties/objectForm'

const form = defineModel<ObjectForm>('form', { required: true })

const { _t } = usei18n()

const embedOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: 'img', title: _t('Image (img)') },
    { name: 'iframe', title: _t('Interactive (iframe)') }
  ]
}))
</script>

<template>
  <PropertySection :title="_t('URL embed')">
    <PropertyRow :label="_t('URL')">
      <CmkInput
        v-model="form.graph_url"
        :placeholder="untranslated('https://…')"
        field-size="fill"
      />
    </PropertyRow>
    <PropertyRow :label="_t('Embed as')">
      <CmkDropdown
        floating
        :model-value="form.graph_embed_type"
        :options="embedOptions"
        :label="_t('Embed as')"
        width="fill"
        @update:model-value="form.graph_embed_type = ($event ?? 'img') as 'img' | 'iframe'"
      />
    </PropertyRow>
    <PropertyRow :label="_t('Width')">
      <CmkInput v-model="form.graph_width" type="number" min="50" />
    </PropertyRow>
    <PropertyRow :label="_t('Height')">
      <CmkInput v-model="form.graph_height" type="number" min="30" />
    </PropertyRow>
    <PropertyRow :label="_t('Auto-refresh (s)')">
      <CmkInput v-model="form.graph_refresh_interval" type="number" min="0" />
      <span class="maps-graph-embed-section__hint">{{ _t('0 = off') }}</span>
    </PropertyRow>
  </PropertySection>
</template>

<style scoped>
.maps-graph-embed-section__hint {
  font-size: var(--font-size-normal);
  color: var(--font-color-dimmed);
}
</style>
