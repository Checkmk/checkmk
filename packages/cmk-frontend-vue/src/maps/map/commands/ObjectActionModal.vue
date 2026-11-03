<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
One command's form, in the map's dialog. The form is the monitoring pages' own,
so it asks what the host view asks; a refusal stays beside it so the operator
can correct and send again.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import usei18n from 'cmk-ui-library/lib/i18n'
import { ref } from 'vue'

import MapsModal from '@/maps/shared/components/MapsModal.vue'
import type { MapElement } from '@/maps/types/api'
import ActionFeedback, {
  type ActionFeedback as ActionFeedbackResult
} from '@/monitoring/shared/components/action/ActionFeedback.vue'
import type { MonitoringAction } from '@/monitoring/shared/components/action/types'

import CommandObjectName from './CommandObjectName.vue'

const props = defineProps<{
  object: MapElement
  action: MonitoringAction<unknown, MapElement>
  submit: (values: unknown) => Promise<ActionFeedbackResult | null>
}>()

const emit = defineEmits<{ close: [] }>()

const { _t } = usei18n()

const draft = ref(props.action.defaultValues())
const isValid = ref(props.action.form === undefined)
const sending = ref(false)
const failure = ref<ActionFeedbackResult | null>(null)
const failureOpen = ref(false)

async function onSubmit(): Promise<void> {
  if (!isValid.value || sending.value) {
    return
  }
  sending.value = true
  failure.value = null
  try {
    failure.value = await props.submit(draft.value)
    failureOpen.value = failure.value !== null
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <MapsModal :open="true" :title="action.title" :scrolls="false" closable @close="emit('close')">
    <div class="maps-object-action-modal">
      <CommandObjectName :object="object" />
      <p v-for="line in action.description" :key="line" class="maps-object-action-modal__hint">
        {{ line }}
      </p>
      <component
        :is="action.form"
        v-if="action.form"
        v-bind="action.formProps"
        v-model="draft"
        @update:valid="isValid = $event"
      />
      <ActionFeedback v-if="failure" v-model:open="failureOpen" :feedback="failure" />
    </div>

    <template #footer>
      <CmkButton variant="secondary" @click="emit('close')">
        {{ _t('Cancel') }}
      </CmkButton>
      <CmkButton variant="primary" :disabled="!isValid || sending" @click="onSubmit">
        {{ action.submitLabel }}
      </CmkButton>
    </template>
  </MapsModal>
</template>

<style scoped>
/* A fixed width, so opening the downtime form's advanced options, whose labels
   are long, wraps them instead of widening the dialog around the form. */
.maps-object-action-modal {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
  width: min(520px, 80vw);
}

.maps-object-action-modal__hint {
  margin: 0;
  color: var(--font-color-dimmed);
}
</style>
