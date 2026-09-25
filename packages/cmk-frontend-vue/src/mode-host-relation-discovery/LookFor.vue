<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import { CmkRadioButton, CmkRadioGroup } from 'cmk-ui-library/components/user-input/CmkRadioButton'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import useId from 'cmk-ui-library/lib/useId'
import { computed } from 'vue'

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

const kindHeadingId = useId()

const pairNounOf = usePairNoun(() => props.relationNouns)

const words = computed(() => props.kindWords[kind.value] ?? [])

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
    <section class="mode-host-relation-discovery-look-for__section">
      <CmkHeading :id="kindHeadingId" type="h4">{{
        _t('Which hosts belong together?')
      }}</CmkHeading>
      <CmkRadioGroup v-model="kind" :aria-labelledby="kindHeadingId">
        <CmkRadioButton
          v-for="kindId in Object.keys(props.kinds)"
          :key="kindId"
          :value="kindId"
          :label="untranslated(pairNounOf(kindId))"
        />
      </CmkRadioGroup>
    </section>

    <section class="mode-host-relation-discovery-look-for__section">
      <CmkHeading type="h4">{{ _t('Where can Checkmk see it?') }}</CmkHeading>
      <CmkCheckbox
        :model-value="looksIn('names')"
        :label="_t('In the host names')"
        @update:model-value="(wanted) => setLookIn('names', wanted)"
      >
        <CmkParagraph class="mode-host-relation-discovery-look-for__hint">
          {{
            words.length > 0
              ? _t(
                  '"srv-01-%{word}" next to "srv-01", for example. Checkmk knows the usual words - %{words} - and also shows you the other words your host names use.',
                  { word: words[0] ?? '', words: words.join(', ') }
                )
              : _t('One host named like another plus a word, for example.')
          }}
        </CmkParagraph>
      </CmkCheckbox>
      <CmkCheckbox
        :model-value="looksIn('values')"
        :label="_t('In a host label or custom host attribute both hosts carry')"
        @update:model-value="(wanted) => setLookIn('values', wanted)"
      >
        <CmkParagraph class="mode-host-relation-discovery-look-for__hint">
          {{
            _t(
              'A serial number or asset tag from your CMDB, for example. Only needed if your host names do not say which hosts belong together.'
            )
          }}
        </CmkParagraph>
      </CmkCheckbox>
    </section>
  </div>
</template>

<style scoped>
.mode-host-relation-discovery-look-for {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-double);
}

.mode-host-relation-discovery-look-for__section {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-half);
}

.mode-host-relation-discovery-look-for__hint {
  color: var(--font-color-dimmed);
}
</style>
