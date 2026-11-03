<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Members a host, host group or service group leaves out, as NagVis'
exclude_members and exclude_member_states do.
-->
<script setup lang="ts">
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'

import PropertyRow from '@/maps/map/edit/properties/PropertyRow.vue'
import PropertySection from '@/maps/map/edit/properties/PropertySection.vue'
import type { ObjectForm } from '@/maps/map/edit/properties/objectForm'

defineProps<{ isHost: boolean }>()

const form = defineModel<ObjectForm>('form', { required: true })

const { _t } = usei18n()
</script>

<template>
  <PropertySection
    :title="_t('Filter')"
    collapsible
    :default-open="!!(form.exclude_members || form.exclude_member_states)"
  >
    <PropertyRow v-slot="{ id }" labels-control :label="_t('Exclude members')">
      <CmkInput
        :id="id"
        v-model="form.exclude_members"
        :placeholder="untranslated('^test-')"
        field-size="fill"
      />
    </PropertyRow>
    <PropertyRow v-slot="{ id }" labels-control :label="_t('Exclude members from state')">
      <CmkInput
        :id="id"
        v-model="form.exclude_member_states"
        :placeholder="untranslated(isHost ? '^Backup' : '~~^Backup')"
        field-size="fill"
      />
    </PropertyRow>
    <!-- One sentence each: a translator needs the whole thing to reorder it. -->
    <p class="maps-filter-section__hint">
      {{
        isHost
          ? _t('Both take a Livestatus regular expression on the service names of this host.')
          : _t(
              'Both take a Livestatus regular expression on member names; %{pattern} names a service of a member host.',
              { pattern: 'host~~service' }
            )
      }}
    </p>
    <p class="maps-filter-section__hint">
      {{
        _t(
          'Excluded members are left out entirely; members whose state is excluded are still listed but do not count, and that pattern then replaces the first one for the state.'
        )
      }}
    </p>
  </PropertySection>
</template>

<style scoped>
.maps-filter-section__hint {
  margin: 0;
  font-size: var(--font-size-small);
  color: var(--font-color-dimmed);
}
</style>
