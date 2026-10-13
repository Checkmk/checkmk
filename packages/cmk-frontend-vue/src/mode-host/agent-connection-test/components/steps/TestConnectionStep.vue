<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { CmkWizardButton } from 'cmk-ui-library/components/CmkWizard'
import CmkWizardStep from 'cmk-ui-library/components/CmkWizard/CmkWizardStep.vue'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed } from 'vue'

import { type HostMacros, renderBlocks } from '../../lib/commandTemplate'
import type { CommandBlock, CommandChoice, StatusSpec } from '../../lib/types'
import CommandBlockList from '../CommandBlockList.vue'
import ShellToggle from '../ShellToggle.vue'

const props = defineProps<{
  index: number
  isCompleted: () => boolean
  isActive: boolean
  spec: StatusSpec
  macros: HostMacros
  closeButtonTitle: TranslatedString
}>()

const shellId = defineModel<string>('shellId', { default: '' })

const emit = defineEmits<{ close: [] }>()

const { _t } = usei18n()

const variants = computed<CommandChoice[] | null>(() =>
  props.spec.kind === 'shell-variants' ? props.spec.variants : null
)

const blocks = computed<CommandBlock[]>(() => {
  if (props.spec.kind === 'single') {
    return [{ command: props.spec.command }]
  }
  const chosen = variants.value?.find((variant) => variant.id === shellId.value)
  return (chosen ?? variants.value?.[0])?.blocks ?? []
})

const rendered = computed(() => renderBlocks(blocks.value, 'download', props.macros))
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
      <template v-if="isActive">
        <ShellToggle v-if="variants" v-model="shellId" :choices="variants" />
        <CommandBlockList :blocks="rendered.blocks" />
      </template>
    </template>
    <template #actions>
      <CmkWizardButton type="finish" :override-label="closeButtonTitle" @click="emit('close')" />
      <CmkWizardButton type="previous" />
    </template>
  </CmkWizardStep>
</template>
