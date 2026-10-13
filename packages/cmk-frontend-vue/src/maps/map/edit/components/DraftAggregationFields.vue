<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Binding a draft object to a BI aggregation: which aggregation, how deep to
expand it, and what that would look like on the map.
-->
<script setup lang="ts">
import CmkChip from 'cmk-ui-library/components/CmkChip.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import AggregationPreview from '@/maps/map/edit/components/AggregationPreview.vue'
import EditField from '@/maps/map/edit/components/EditField.vue'
import { useAggregationPreview } from '@/maps/map/edit/composables/useAggregationPreview'
import type { ObjectSuggestions } from '@/maps/map/edit/composables/useObjectSuggestions'
import MapsSuggestionField from '@/maps/shared/components/MapsSuggestionField.vue'

const props = defineProps<{
  suggestions: ObjectSuggestions
  connectionId: string
}>()

const aggregationId = defineModel<string>('aggregationId', { required: true })
const expandDepth = defineModel<number>('expandDepth', { required: true })

const { _t } = usei18n()

const preview = useAggregationPreview({
  connectionId: () => props.connectionId,
  aggregationId: () => aggregationId.value,
  expandDepth: () => expandDepth.value
})

const aggregationFunction = computed(() =>
  props.suggestions.aggregationFunctionOf(aggregationId.value)
)
</script>

<template>
  <EditField :label="_t('BI aggregation')" required>
    <MapsSuggestionField
      v-model="aggregationId"
      :label="_t('BI aggregation')"
      :list="suggestions.aggregations"
      :placeholder="_t('Select an aggregation')"
      :empty-hint="
        _t(
          'No BI aggregations available — none are configured in Checkmk, or your user has no permission to view them.'
        )
      "
    />
  </EditField>

  <!--
    The aggregation's top-level function (worst / best / count_ok /
    state_of_host / …) as Checkmk reports it, so the designer can see the
    semantics without crosschecking the setup. Absent until an aggregation is
    picked, and on Checkmk versions that do not surface it.
  -->
  <CmkChip
    v-if="aggregationFunction"
    as-div
    size="small"
    variant="outline"
    color="others"
    :title="
      _t(
        'Top-level aggregation function from Checkmk (e.g. worst, best, count_ok). Configured in the setup.'
      )
    "
  >
    {{ _t('Function') }}: {{ aggregationFunction }}
  </CmkChip>

  <EditField
    :label="_t('Expand depth')"
    :help="_t('Show child nodes up to N levels (0 = root only).')"
  >
    <CmkInput v-model="expandDepth" type="number" min="0" max="10" field-size="small" />
  </EditField>

  <AggregationPreview
    :tree="preview.tree.value"
    :connection-ok="preview.connectionOk.value"
    :aggregation-id="aggregationId"
    :expand-depth="expandDepth"
  />
</template>
