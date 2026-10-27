<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
What the object says when hovered or right-clicked, written as a template over
its own live state.
-->
<script setup lang="ts">
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import PropertyRow from '@/maps/map/edit/properties/PropertyRow.vue'
import PropertySection from '@/maps/map/edit/properties/PropertySection.vue'
import type { ObjectForm } from '@/maps/map/edit/properties/objectForm'

const form = defineModel<ObjectForm>('form', { required: true })

const props = defineProps<{
  /** Without a monitoring state, only the object's own name fills in. */
  stateful: boolean
}>()

const { _t } = usei18n()

// The placeholders are literal mustaches: built here so the template below
// interpolates the sentence rather than the placeholders themselves.
const placeholderHint = computed(() =>
  props.stateful
    ? _t(
        'Available: {{name}}, {{state}}, {{output}}, {{host}}, {{service}}, {{address}}, {{state_type}}, {{attempts}}, {{last_check}}, {{state_duration}}, {{acknowledged}}, {{in_downtime}}, {{stale}}'
      )
    : _t('Available: {{name}}')
)
const exampleTemplate = computed(() =>
  props.stateful ? _t('e.g. {{name}} is {{state}}') : _t('e.g. {{name}}')
)
</script>

<template>
  <PropertySection
    :title="_t('Templates')"
    collapsible
    :default-open="!!(form.hover_template || form.context_template || form.hover_url)"
  >
    <PropertyRow v-slot="{ id }" labels-control :label="_t('Hover template')">
      <CmkInput
        :id="id"
        v-model="form.hover_template"
        :placeholder="exampleTemplate"
        field-size="fill"
      />
    </PropertyRow>
    <PropertyRow v-slot="{ id }" labels-control :label="_t('Hover URL')">
      <CmkInput
        :id="id"
        v-model="form.hover_url"
        :placeholder="untranslated('https://…')"
        field-size="fill"
      />
    </PropertyRow>
    <PropertyRow v-slot="{ id }" labels-control :label="_t('Context template')">
      <CmkInput
        :id="id"
        v-model="form.context_template"
        :placeholder="exampleTemplate"
        field-size="fill"
      />
    </PropertyRow>
    <p class="maps-templates-section__hint">{{ placeholderHint }}</p>
  </PropertySection>
</template>

<style scoped>
.maps-templates-section__hint {
  margin: 0;
  font-size: var(--font-size-small);
  color: var(--font-color-dimmed);
}
</style>
