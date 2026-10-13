<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Where a click on the object leads. Left empty it goes to the object's own page
in Checkmk, which the field offers as its placeholder.
-->
<script setup lang="ts">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import PropertyRow from '@/maps/map/edit/properties/PropertyRow.vue'
import PropertySection from '@/maps/map/edit/properties/PropertySection.vue'
import type { ObjectForm } from '@/maps/map/edit/properties/objectForm'

const props = defineProps<{
  /** The object's own page in Checkmk, when one can be derived. */
  autoUrl: string | null
}>()

const form = defineModel<ObjectForm>('form', { required: true })

const { _t } = usei18n()

const targetOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: '_blank', title: untranslated(`${_t('New tab')} (_blank)`) },
    { name: '_self', title: untranslated(`${_t('Same tab')} (_self)`) },
    { name: '_top', title: untranslated(`${_t('Top frame')} (_top)`) }
  ]
}))

const offersAutoUrl = computed(() => !!props.autoUrl && !form.value.url)
</script>

<template>
  <PropertySection
    :title="_t('Link')"
    collapsible
    :default-open="!!form.url"
    :side-title="untranslated(form.url)"
  >
    <PropertyRow :label="_t('URL')" tall>
      <div class="maps-link-section__url">
        <CmkInput
          v-model="form.url"
          :placeholder="untranslated(autoUrl ?? 'https://…')"
          field-size="fill"
        />
        <button
          v-if="offersAutoUrl"
          type="button"
          class="maps-link-section__adopt"
          @click="form.url = autoUrl ?? ''"
        >
          {{ _t('Automatically derived from Checkmk URL when left empty') }}
          {{ untranslated('→') }}
        </button>
      </div>
    </PropertyRow>
    <PropertyRow :label="_t('Target')">
      <CmkDropdown
        floating
        :model-value="form.url_target"
        :options="targetOptions"
        :label="_t('Target')"
        width="fill"
        @update:model-value="form.url_target = $event ?? ''"
      />
    </PropertyRow>
  </PropertySection>
</template>

<style scoped>
.maps-link-section__url {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: var(--dimension-3);
  min-width: 0;
}

.maps-link-section__adopt {
  font-size: var(--font-size-small);
  color: var(--font-color-dimmed);
  text-align: left;
}

.maps-link-section__adopt:hover {
  color: var(--font-color);
}
</style>
