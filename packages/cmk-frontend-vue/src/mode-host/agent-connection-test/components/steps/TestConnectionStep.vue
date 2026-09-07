<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkCode from 'cmk-ui-library/components/CmkCode.vue'
import CmkToggleButtonGroup from 'cmk-ui-library/components/CmkToggleButtonGroup.vue'
import { CmkWizardButton } from 'cmk-ui-library/components/CmkWizard'
import CmkWizardStep from 'cmk-ui-library/components/CmkWizard/CmkWizardStep.vue'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed } from 'vue'

import type { AgentSlideOutTabs } from '../../lib/type_def'

const props = defineProps<{
  index: number
  isCompleted: () => boolean
  isActive: boolean
  tab: AgentSlideOutTabs
  closeButtonTitle: TranslatedString
}>()

const selectedVariantId = defineModel<string>('selectedVariantId', { default: '' })

const emit = defineEmits<{ close: [] }>()

const { _t } = usei18n()

const statusCmd = computed(() => {
  const variants = props.tab.statusCmdVariants
  if (variants && variants.length > 0) {
    return variants.find((v) => v.id === selectedVariantId.value)?.cmd ?? variants[0]!.cmd
  }
  return props.tab.statusCmd
})
</script>

<template>
  <CmkWizardStep :index="index" :is-completed="isCompleted">
    <template #header>
      <CmkHeading> {{ _t('Test connection') }}</CmkHeading>
    </template>
    <template #content>
      <CmkParagraph>
        {{
          _t(`Test if you have configured everything correctly with pasting the following
                  command into the CLI of the target system.`)
        }}
      </CmkParagraph>
      <CmkToggleButtonGroup
        v-if="isActive && tab.statusCmdVariants && tab.statusCmdVariants.length > 1"
        v-model="selectedVariantId"
        class="shell-toggle"
        :options="tab.statusCmdVariants.map((v) => ({ label: v.label, value: v.id }))"
      />
      <CmkCode v-if="isActive" :code-text="statusCmd" class="code" width="fill" />
    </template>
    <template #actions>
      <CmkWizardButton type="finish" :override-label="closeButtonTitle" @click="emit('close')" />
      <CmkWizardButton type="previous" />
    </template>
  </CmkWizardStep>
</template>

<style scoped>
/* stylelint-disable checkmk/vue-bem-naming-convention */
.code {
  margin: var(--dimension-5) 0 var(--dimension-7);
  width: 100%;
}

.shell-toggle {
  margin-top: var(--dimension-5);
  margin-bottom: var(--dimension-5);
}
</style>
