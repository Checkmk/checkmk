<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Adding an object to a map: pick a type, say what it shows, then place it.

While placing, the panel shrinks to its header: the draft is already described,
and the fields would otherwise cover the corner of the canvas the object is
being placed on -- a click there would land on the panel rather than the map.

The type is picked here and nowhere else — the panel is the single surface for
building the draft, so there is no second list competing with it for the corner
it sits in.

The draft belongs to the map editor (``useMapEditor``) and is passed in by
reference — the panel edits it in place so the canvas can already draw the
object being placed.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import CmkIconButton from 'cmk-ui-library/components/CmkIconButton.vue'
import CmkScrollContainer from 'cmk-ui-library/components/CmkScrollContainer.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, watch } from 'vue'

import type { NewObjectDraft } from '@/maps/map/composables/useMapEditor'
import DraftFields from '@/maps/map/edit/components/DraftFields.vue'
import EditField from '@/maps/map/edit/components/EditField.vue'
import { useObjectSuggestions } from '@/maps/map/edit/composables/useObjectSuggestions'
import { clearDraftBindings, isDraftPlaceable } from '@/maps/map/edit/draftFacts'
import type { ObjectType } from '@/maps/types/api'
import { placeableObjectTypes } from '@/maps/utils/dropdownOptions'

const props = defineProps<{
  placing: boolean
  connectionId: string
}>()

// The shared reactive draft owned by useMapEditor. A model rather than a prop:
// the panel writes to its fields, which would otherwise be a prop mutation.
const draft = defineModel<NewObjectDraft>('draft', { required: true })

const emit = defineEmits<{
  'start-placing': []
  'cancel-add': []
}>()

const { _t } = usei18n()

const objectTypeOptions = computed(() => ({
  type: 'filtered' as const,
  suggestions: placeableObjectTypes(_t)
}))

const suggestions = useObjectSuggestions({
  connectionId: () => props.connectionId,
  objectType: () => draft.value.type,
  hostName: () => draft.value.host_name
})

const canPlace = computed(() => isDraftPlaceable(draft.value))

// Bindings never carry over to another type: a hostname left on a draft
// switched to "textbox" would end up on the placed object.
watch(
  () => draft.value.type,
  () => clearDraftBindings(draft.value)
)
</script>

<template>
  <div class="maps-edit-panel" role="group" :aria-label="_t('Add object')">
    <div class="maps-edit-panel__header">
      <CmkIcon name="add" size="small" />
      <div class="maps-edit-panel__heading">
        <p class="maps-edit-panel__title">{{ _t('Add object') }}</p>
        <p class="maps-edit-panel__hint" :class="{ 'maps-edit-panel__hint--placing': placing }">
          {{ placing ? _t('Click on map to place…') : _t('Say what it shows, then place it') }}
        </p>
      </div>
      <CmkIconButton
        name="close"
        size="small"
        :title="_t('Close')"
        :aria-label="_t('Close')"
        @click="emit('cancel-add')"
      />
    </div>

    <CmkScrollContainer v-if="!placing" class="maps-edit-panel__form" height="auto">
      <EditField :label="_t('Object type')" required>
        <CmkDropdown
          floating
          :model-value="draft.type || null"
          :options="objectTypeOptions"
          :input-hint="_t('Select a type')"
          :label="_t('Object type')"
          :no-results-hint="_t('No results found')"
          width="fill"
          @update:model-value="draft.type = ($event ?? '') as ObjectType | ''"
        />
      </EditField>

      <DraftFields v-model:draft="draft" :suggestions="suggestions" :connection-id="connectionId" />
    </CmkScrollContainer>

    <div v-if="draft.type && !placing" class="maps-edit-panel__footer">
      <CmkButton
        variant="primary"
        :disabled="!canPlace"
        class="maps-edit-panel__place"
        @click="canPlace && emit('start-placing')"
      >
        {{ _t('Place on map') }}
      </CmkButton>
    </div>
  </div>
</template>

<style scoped>
.maps-edit-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  font-size: var(--font-size-large);
  line-height: 20px;
}

.maps-edit-panel__header {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: var(--dimension-4);
  padding: var(--spacing) var(--dimension-6);
  border-bottom: 1px solid var(--default-border-color);
}

.maps-edit-panel__heading {
  flex: 1;
  min-width: 0;
}

.maps-edit-panel__title {
  margin: 0;
  font-size: var(--font-size-large);
  font-weight: var(--font-weight-bold);
  line-height: 20px;
  color: var(--font-color);
}

.maps-edit-panel__hint {
  margin: var(--dimension-2) 0 0;
  font-size: var(--font-size-small);
  color: var(--font-color-dimmed);
}

.maps-edit-panel__hint--placing {
  color: var(--color-yellow-50);
}

/* The scroll container is itself the field column: a gap rather than sibling
   margins, because the per-type fields come from a component that renders
   several roots at once, which sibling selectors in scoped CSS cannot reach. */
.maps-edit-panel__form {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
  gap: var(--dimension-5);
  padding: var(--dimension-5) var(--dimension-6);
}

.maps-edit-panel__footer {
  flex-shrink: 0;
  padding: 0 var(--dimension-6) var(--dimension-5);
}

.maps-edit-panel__place {
  width: 100%;
}
</style>
