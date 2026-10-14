<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
What the object stands for: the connection it reads from, and the monitoring
object it is bound to — which differs per object type. A line picks the type
of object it shows the state of.
-->
<script setup lang="ts">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import { useConnectionOverride } from '@/maps/map/edit/composables/useConnectionOverride'
import type { ObjectSuggestions } from '@/maps/map/edit/composables/useObjectSuggestions'
import { rebindHost } from '@/maps/map/edit/hostBinding'
import PropertyRow from '@/maps/map/edit/properties/PropertyRow.vue'
import PropertySection from '@/maps/map/edit/properties/PropertySection.vue'
import {
  type ObjectForm,
  boundTypeOf,
  choosesServiceCounting,
  hasStateOptions
} from '@/maps/map/edit/properties/objectForm'
import MapsColorInput from '@/maps/shared/components/MapsColorInput.vue'
import MapsObjectField from '@/maps/shared/components/MapsObjectField.vue'
import MapsSuggestionField from '@/maps/shared/components/MapsSuggestionField.vue'
import MapsTextArea from '@/maps/shared/components/MapsTextArea.vue'
import type { MapElement, MonitoredObjectType } from '@/maps/types/api'
import { dyngroupTypeOptions, lineObjectTypeOptions } from '@/maps/utils/dropdownOptions'

const props = defineProps<{
  object: MapElement
  suggestions: ObjectSuggestions
}>()

const form = defineModel<ObjectForm>('form', { required: true })

const { _t } = usei18n()

const { options: connectionOptions } = useConnectionOverride()

const dyngroupTypeSuggestions = computed(() => ({
  type: 'fixed' as const,
  suggestions: dyngroupTypeOptions(_t)
}))

const lineObjectTypeSuggestions = computed(() => ({
  type: 'fixed' as const,
  suggestions: lineObjectTypeOptions(_t)
}))

const isLine = computed(() => props.object.type === 'line')
const type = computed(() => boundTypeOf(form.value, props.object))
/** Only an expanded aggregation draws the lines down to its subtree. */
const showsSubtreeLines = computed(() => !isLine.value && form.value.expand_depth > 0)

const showsStateChecks = computed(() => hasStateOptions(type.value))
const showsRecognizeServices = computed(() => choosesServiceCounting(type.value, form.value))
</script>

<template>
  <PropertySection :title="_t('Monitoring object')">
    <PropertyRow :label="_t('Connection')">
      <CmkDropdown
        floating
        :model-value="form.connection_id"
        :options="connectionOptions"
        :label="_t('Connection')"
        width="fill"
        @update:model-value="form.connection_id = $event ?? ''"
      />
    </PropertyRow>

    <PropertyRow v-if="isLine" :label="_t('Shows the state of')">
      <CmkDropdown
        floating
        :model-value="form.line_object_type"
        :options="lineObjectTypeSuggestions"
        :label="_t('Shows the state of')"
        width="fill"
        @update:model-value="form.line_object_type = ($event ?? 'host') as MonitoredObjectType"
      />
    </PropertyRow>

    <template v-if="type === 'host' || type === 'service'">
      <PropertyRow :label="_t('Host name')">
        <MapsObjectField
          :model-value="form.host_name"
          kind="host"
          :label="_t('Host name')"
          :placeholder="_t('hostname')"
          @update:model-value="rebindHost(form, $event)"
        />
      </PropertyRow>
      <PropertyRow v-if="type === 'service'" :label="_t('Service')">
        <MapsObjectField
          v-model="form.service_description"
          kind="service"
          :host-name="form.host_name"
          :label="_t('Service')"
          :placeholder="_t('service description')"
        />
      </PropertyRow>
    </template>

    <template v-if="type === 'hostgroup' || type === 'servicegroup'">
      <PropertyRow :label="_t('Group name')">
        <MapsObjectField
          v-model="form.group_name"
          :kind="type"
          :label="_t('Group name')"
          :placeholder="_t('group name')"
        />
      </PropertyRow>
    </template>

    <template v-if="type === 'dyngroup'">
      <PropertyRow :label="_t('Filter on')">
        <CmkDropdown
          floating
          :model-value="form.object_types"
          :options="dyngroupTypeSuggestions"
          :label="_t('Filter on')"
          width="fill"
          @update:model-value="form.object_types = ($event ?? 'host') as 'host' | 'service'"
        />
      </PropertyRow>
      <PropertyRow v-slot="{ id }" labels-control :label="_t('Livestatus filter')" tall>
        <MapsTextArea
          :id="id"
          v-model="form.object_filter"
          :rows="4"
          monospace
          :placeholder="untranslated('Filter: host_name ~ ^web')"
        />
      </PropertyRow>
      <!-- One sentence, not five fragments: a translator needs the whole
           thing to put the words in their language's order. -->
      <p class="maps-identity-section__note">
        {{
          _t(
            'One or more %{filter} lines, each terminated by a literal %{newline}. Forwarded verbatim to Livestatus against %{query}.',
            { filter: 'Filter:', newline: '\\n', query: 'GET hosts/services' }
          )
        }}
      </p>
    </template>

    <div v-if="showsStateChecks" class="maps-identity-section__checks">
      <CmkCheckbox v-model="form.only_hard_states" :label="_t('Only hard states')" />
      <CmkCheckbox
        v-if="showsRecognizeServices"
        v-model="form.recognize_services"
        :label="_t('Consider services')"
      />
    </div>

    <PropertyRow v-if="type === 'map'" :label="_t('Map name')">
      <MapsSuggestionField
        v-model="form.map_name"
        :label="_t('Map name')"
        :list="suggestions.maps"
        :placeholder="_t('map-name')"
        :empty-hint="_t('No other maps available')"
      />
    </PropertyRow>

    <template v-if="type === 'aggregation'">
      <PropertyRow :label="_t('BI aggregation')">
        <MapsSuggestionField
          v-model="form.aggregation_id"
          :label="_t('BI aggregation')"
          :list="suggestions.aggregations"
          :placeholder="_t('aggregation id')"
          :empty-hint="
            _t(
              'No BI aggregations available — none are configured in Checkmk, or your user has no permission to view them.'
            )
          "
        />
      </PropertyRow>
      <PropertyRow v-if="!isLine" v-slot="{ id }" labels-control :label="_t('Expand depth')">
        <CmkInput
          :id="id"
          v-model="form.expand_depth"
          type="number"
          min="0"
          max="10"
          :title="_t('Show child nodes up to N levels (0 = root only).')"
        />
      </PropertyRow>
      <PropertyRow
        v-if="showsSubtreeLines"
        v-slot="{ id, label }"
        labels-control
        :label="_t('Subtree line')"
      >
        <MapsColorInput
          v-model="form.line_color"
          :label="label"
          :input-id="id"
          :enable-label="_t('Use color')"
          default-color="#a1a1aa"
        />
      </PropertyRow>
      <PropertyRow
        v-if="showsSubtreeLines"
        v-slot="{ id }"
        labels-control
        :label="_t('Subtree width')"
      >
        <CmkInput
          :id="id"
          v-model="form.line_width"
          type="number"
          :min="1"
          :max="20"
          :placeholder="_t('auto')"
        />
      </PropertyRow>
    </template>
  </PropertySection>
</template>

<style scoped>
.maps-identity-section__checks {
  display: flex;
  flex-wrap: wrap;
  gap: var(--dimension-5);
}

.maps-identity-section__note {
  margin: 0;
  font-size: var(--font-size-small);
  color: var(--font-color-dimmed);
}
</style>
