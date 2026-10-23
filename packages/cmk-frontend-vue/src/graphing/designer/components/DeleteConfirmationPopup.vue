<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkPopup from 'cmk-ui-library/components/CmkPopup.vue'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { DialogTitle } from 'reka-ui'
import { computed } from 'vue'

import type { PendingDelete } from '../composables/useDeleteConfirmation'
import { useItemDescription } from '../composables/useItemDescription'

const { _t, _tn } = usei18n()

const { pending } = defineProps<{
  open: boolean
  pending: PendingDelete
}>()

const emit = defineEmits<{
  /** Delete the targets and all their dependents. */
  confirm: []
  close: []
}>()

const { describeFormula } = useItemDescription()

const title = computed(() =>
  pending.all
    ? _t('Delete all metrics?')
    : _tn('Delete metric %{names}?', 'Delete metrics %{names}?', pending.targets.length, {
        names: pending.targets.map((target) => target.name).join(', ')
      })
)
</script>

<template>
  <CmkPopup :open="open" @close="emit('close')">
    <div class="graphing-delete-confirmation-popup">
      <DialogTitle>
        <CmkHeading type="h2">{{ title }}</CmkHeading>
      </DialogTitle>
      <CmkParagraph>{{ _t('This action can’t be undone.') }}</CmkParagraph>
      <template v-if="pending.dependents.length > 0">
        <CmkParagraph>
          {{
            _tn(
              'Calculations that use this metric are also deleted:',
              'Calculations that use these metrics are also deleted:',
              pending.targets.length
            )
          }}
        </CmkParagraph>
        <ul class="graphing-delete-confirmation-popup__dependents">
          <li v-for="dependent in pending.dependents" :key="dependent.id">
            {{ dependent.id }} = {{ describeFormula(dependent.ast) }}
          </li>
        </ul>
      </template>
      <div class="graphing-delete-confirmation-popup__buttons">
        <CmkButton variant="danger" @click="emit('confirm')">
          {{ pending.all ? _t('Delete all') : _t('Delete') }}
        </CmkButton>
        <CmkButton variant="secondary" @click="emit('close')">
          {{ _t('Cancel') }}
        </CmkButton>
      </div>
    </div>
  </CmkPopup>
</template>

<style scoped>
.graphing-delete-confirmation-popup {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-6);
}

.graphing-delete-confirmation-popup__dependents {
  margin: 0;
  padding-left: var(--dimension-8);
}

.graphing-delete-confirmation-popup__buttons {
  display: flex;
  gap: var(--dimension-4);
}
</style>
