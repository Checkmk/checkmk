<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The fields that bind a draft object to what it shows — a different set per
object type, which is why they live here rather than in the panel around them.

Every field carries its label above it (``EditField``) rather than only inside
the control: a placeholder disappears the moment something is typed, and
"(required)" is what says why the place button is still disabled.
-->
<script setup lang="ts">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import ImagePicker from '@/maps/image-library/components/ImagePicker.vue'
import type { NewObjectDraft } from '@/maps/map/composables/useMapEditor'
import DraftAggregationFields from '@/maps/map/edit/components/DraftAggregationFields.vue'
import EditField from '@/maps/map/edit/components/EditField.vue'
import type { ObjectSuggestions } from '@/maps/map/edit/composables/useObjectSuggestions'
import MapsSuggestionField from '@/maps/shared/components/MapsSuggestionField.vue'
import MapsTextArea from '@/maps/shared/components/MapsTextArea.vue'
import { dyngroupTypeOptions } from '@/maps/utils/dropdownOptions'

defineProps<{
  suggestions: ObjectSuggestions
  connectionId: string
}>()

const draft = defineModel<NewObjectDraft>('draft', { required: true })

const { _t } = usei18n()

const dyngroupTypeSuggestions = computed(() => ({
  type: 'fixed' as const,
  suggestions: dyngroupTypeOptions(_t)
}))
</script>

<template>
  <template v-if="draft.type === 'host'">
    <EditField :label="_t('Host name')" required>
      <MapsSuggestionField
        v-model="draft.host_name"
        :label="_t('Host name')"
        :list="suggestions.hosts"
        :placeholder="_t('Select a host')"
        :empty-hint="_t('No hosts available')"
      />
    </EditField>
  </template>

  <template v-else-if="draft.type === 'service'">
    <EditField :label="_t('Host name')" required>
      <MapsSuggestionField
        v-model="draft.host_name"
        :label="_t('Host name')"
        :list="suggestions.hosts"
        :placeholder="_t('Select a host')"
        :empty-hint="_t('No hosts available')"
      />
    </EditField>
    <EditField :label="_t('Service description')" required>
      <MapsSuggestionField
        v-model="draft.service_description"
        :label="_t('Service description')"
        :list="suggestions.services"
        :placeholder="draft.host_name ? _t('Select a service') : _t('Pick a host first')"
        :empty-hint="draft.host_name ? _t('No services for this host') : undefined"
      />
    </EditField>
  </template>

  <template v-else-if="draft.type === 'hostgroup' || draft.type === 'servicegroup'">
    <EditField :label="_t('Group name')" required>
      <MapsSuggestionField
        v-model="draft.group_name"
        :label="_t('Group name')"
        :list="suggestions.groups"
        :placeholder="_t('Select a group')"
        :empty-hint="
          draft.type === 'hostgroup'
            ? _t('No host groups configured in this site')
            : _t('No service groups configured in this site')
        "
      />
    </EditField>
  </template>

  <template v-else-if="draft.type === 'map'">
    <EditField :label="_t('Map name')" required>
      <MapsSuggestionField
        v-model="draft.map_name"
        :label="_t('Map name')"
        :list="suggestions.maps"
        :placeholder="_t('Select a map')"
        :empty-hint="_t('No other maps available')"
      />
    </EditField>
    <EditField :label="_t('Label')">
      <CmkInput v-model="draft.label_text" :placeholder="_t('optional')" field-size="fill" />
    </EditField>
  </template>

  <template v-else-if="draft.type === 'aggregation'">
    <DraftAggregationFields
      v-model:aggregation-id="draft.aggregation_id"
      v-model:expand-depth="draft.expand_depth"
      :suggestions="suggestions"
      :connection-id="connectionId"
    />
  </template>

  <template v-else-if="draft.type === 'dyngroup'">
    <EditField :label="_t('Filter on')">
      <CmkDropdown
        floating
        :model-value="draft.object_types"
        :options="dyngroupTypeSuggestions"
        :label="_t('Filter on')"
        width="fill"
        @update:model-value="draft.object_types = ($event ?? 'host') as 'host' | 'service'"
      />
    </EditField>
    <EditField
      :label="_t('Livestatus filter')"
      :help="_t('One or more Filter: lines, forwarded verbatim to Livestatus.')"
      required
    >
      <MapsTextArea
        v-model="draft.object_filter"
        monospace
        :placeholder="untranslated('Filter: host_name ~ ^web')"
      />
    </EditField>
  </template>

  <template v-else-if="draft.type === 'line'">
    <EditField :label="_t('Host name')">
      <MapsSuggestionField
        v-model="draft.host_name"
        :label="_t('Host name')"
        :list="suggestions.hosts"
        :placeholder="_t('optional')"
        :empty-hint="_t('No hosts available')"
      />
    </EditField>
    <EditField :label="_t('Service description')">
      <MapsSuggestionField
        v-model="draft.service_description"
        :label="_t('Service description')"
        :list="suggestions.services"
        :placeholder="_t('optional')"
      />
    </EditField>
  </template>

  <template v-else-if="draft.type === 'textbox'">
    <EditField :label="_t('Text content')">
      <CmkInput v-model="draft.label_text" :placeholder="_t('optional')" field-size="fill" />
    </EditField>
  </template>

  <template v-else-if="draft.type === 'image'">
    <EditField :label="_t('Image')" required>
      <ImagePicker v-model="draft.image_src" />
    </EditField>
    <EditField :label="_t('Label')">
      <CmkInput v-model="draft.label_text" :placeholder="_t('optional')" field-size="fill" />
    </EditField>
  </template>

  <template v-else-if="draft.type === 'graph'">
    <EditField :label="_t('Host name')">
      <MapsSuggestionField
        v-model="draft.host_name"
        :label="_t('Host name')"
        :list="suggestions.hosts"
        :placeholder="_t('Select a host')"
        :empty-hint="_t('No hosts available')"
      />
    </EditField>
    <EditField :label="_t('Service description')">
      <MapsSuggestionField
        v-model="draft.service_description"
        :label="_t('Service description')"
        :list="suggestions.services"
        :placeholder="_t('optional')"
      />
    </EditField>
    <EditField :label="_t('URL')">
      <CmkInput
        v-model="draft.graph_url"
        :placeholder="_t('optional')"
        field-size="fill"
        class="maps-draft-fields__url"
      />
    </EditField>
  </template>
</template>

<style scoped>
.maps-draft-fields__url {
  font-family: monospace;
}
</style>
