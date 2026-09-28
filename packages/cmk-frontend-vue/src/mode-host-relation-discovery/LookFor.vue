<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import type { Suggestions as DropdownOptions } from 'cmk-ui-library/components/CmkSuggestions'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import useId from 'cmk-ui-library/lib/useId'
import { computed } from 'vue'

import LabeledRow from './LabeledRow.vue'
import { usePairNoun } from './relationWording'
import type { LookIn } from './types'

const { _t } = usei18n()

const props = defineProps<{
  kinds: Record<string, string>
  kindWords: Record<string, string[]>
  relationNouns: Record<string, string>
}>()

const kind = defineModel<string>('kind', { required: true })
const lookIn = defineModel<LookIn[]>('lookIn', { required: true })

const kindId = useId()
const indicatorsId = useId()

const pairNounOf = usePairNoun(() => props.relationNouns)

const kindIds = computed(() => Object.keys(props.kinds))
const kindOptions = computed<DropdownOptions>(() => ({
  type: 'fixed',
  suggestions: kindIds.value.map((id) => ({ name: id, title: untranslated(pairNounOf(id)) }))
}))
const namesHelp = computed(() => {
  const words = props.kindWords[kind.value] ?? []
  return words.length > 0
    ? _t(
        '"srv-01-%{word}" next to "srv-01", for example. Checkmk knows the usual words - %{words} - and also shows you the other words your host names use.',
        { word: words[0] ?? '', words: words.join(', ') }
      )
    : _t('One host named like another plus a word, for example.')
})

function looksIn(where: LookIn): boolean {
  return lookIn.value.includes(where)
}

function setLookIn(where: LookIn, wanted: boolean): void {
  const others = lookIn.value.filter((other) => other !== where)
  lookIn.value = wanted ? [...others, where] : others
}
</script>

<template>
  <div class="mode-host-relation-discovery-look-for">
    <LabeledRow :label="_t('Relation type')" :for="kindIds.length > 1 ? kindId : undefined">
      <CmkDropdown
        v-if="kindIds.length > 1"
        :component-id="kindId"
        :model-value="kind"
        :options="kindOptions"
        :label="_t('Relation type')"
        @update:model-value="(picked) => (kind = picked ?? kind)"
      />
      <span v-else>{{ pairNounOf(kind) }}</span>
    </LabeledRow>

    <LabeledRow :label="_t('Relation indicators')" :label-id="indicatorsId">
      <div role="group" :aria-labelledby="indicatorsId">
        <CmkCheckbox
          :model-value="looksIn('names')"
          :label="_t('Host names')"
          :help="namesHelp"
          @update:model-value="(wanted) => setLookIn('names', wanted)"
        />
        <CmkCheckbox
          :model-value="looksIn('values')"
          :label="_t('Host labels and custom host attributes')"
          :help="
            _t(
              'A serial number or asset tag from your CMDB that both hosts carry, for example. Only needed if your host names do not say which hosts belong together.'
            )
          "
          @update:model-value="(wanted) => setLookIn('values', wanted)"
        />
      </div>
    </LabeledRow>
  </div>
</template>

<style scoped>
.mode-host-relation-discovery-look-for {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
}
</style>
