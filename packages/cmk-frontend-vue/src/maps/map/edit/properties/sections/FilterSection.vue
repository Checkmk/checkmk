<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Members an aggregating object leaves out. The count below the fields says what
the pattern would actually suppress, which turns a guess into something the
operator can check before saving.
-->
<script setup lang="ts">
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'

import { useExcludeMembersPreview } from '@/maps/map/edit/composables/useExcludeMembersPreview'
import PropertyRow from '@/maps/map/edit/properties/PropertyRow.vue'
import PropertySection from '@/maps/map/edit/properties/PropertySection.vue'
import type { ObjectForm } from '@/maps/map/edit/properties/objectForm'

const props = defineProps<{ connectionId: string }>()

const form = defineModel<ObjectForm>('form', { required: true })

const { _t } = usei18n()

const { feedback } = useExcludeMembersPreview({
  connectionId: () => props.connectionId,
  aggregationId: () => form.value.aggregation_id,
  excludeMembers: () => form.value.exclude_members,
  excludeMemberStates: () => form.value.exclude_member_states
})
</script>

<template>
  <PropertySection
    :title="_t('Filter')"
    collapsible
    :default-open="!!(form.exclude_members || form.exclude_member_states)"
  >
    <PropertyRow :label="_t('Exclude members')">
      <CmkInput
        v-model="form.exclude_members"
        :placeholder="_t('regex pattern…')"
        field-size="fill"
      />
    </PropertyRow>
    <PropertyRow :label="_t('Exclude states')">
      <CmkInput
        v-model="form.exclude_member_states"
        :placeholder="untranslated('DOWN,CRITICAL')"
        field-size="fill"
      />
    </PropertyRow>
    <p
      v-if="feedback"
      class="maps-filter-section__feedback"
      :class="`maps-filter-section__feedback--${feedback.tone}`"
    >
      {{ feedback.text }}
    </p>
    <p class="maps-filter-section__hint">
      {{ _t('Regex to exclude members / comma-separated states to ignore') }}
    </p>
  </PropertySection>
</template>

<style scoped>
.maps-filter-section__feedback {
  margin: 0;
  font-size: var(--font-size-normal);
}

.maps-filter-section__feedback--invalid {
  color: var(--color-state-critical);
}

.maps-filter-section__feedback--warn {
  color: var(--color-state-warning);
}

.maps-filter-section__feedback--matched {
  color: var(--color-state-ok);
}

.maps-filter-section__feedback--muted {
  color: var(--font-color-dimmed);
}

.maps-filter-section__hint {
  margin: 0;
  font-size: var(--font-size-small);
  color: var(--font-color-dimmed);
}
</style>
