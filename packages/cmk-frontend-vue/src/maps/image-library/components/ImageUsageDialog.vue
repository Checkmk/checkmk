<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
What deleting an image would break: the maps still referencing it, each a link
to open. Mirrors Checkmk's own "still in use" pattern (CmkSlideInDialog with
link cards) so a long list scrolls instead of overflowing a modal.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkLinkCard from 'cmk-ui-library/components/CmkLinkCard/CmkLinkCard.vue'
import CmkLinkCardContainer from 'cmk-ui-library/components/CmkLinkCard/CmkLinkCardContainer.vue'
import CmkSlideInDialog from 'cmk-ui-library/components/CmkSlideInDialog.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import { useNavigation } from '@/maps/services/context'
import type { ImageUsageEntry } from '@/maps/types/api'

const props = defineProps<{
  open: boolean
  imageName: string
  usage: ImageUsageEntry[]
}>()

const emit = defineEmits<{ confirm: []; cancel: [] }>()

const { _t, _tn } = usei18n()
const nav = useNavigation()

function usageSubtitle(entry: ImageUsageEntry): TranslatedString {
  const parts: TranslatedString[] = []
  if (entry.is_background) {
    parts.push(_t('as background'))
  }
  if (entry.object_ids.length) {
    parts.push(
      _tn('%{n} object', '%{n} objects', entry.object_ids.length, { n: entry.object_ids.length })
    )
  }
  return untranslated(parts.join(', '))
}
</script>

<template>
  <CmkSlideInDialog
    :open="props.open"
    :header="{
      title: _t('Image is still in use'),
      icon: { name: 'warning', size: 'large' },
      closeButton: true
    }"
    size="medium"
    border-color="default"
    @close="emit('cancel')"
  >
    <div class="maps-image-usage-dialog">
      <CmkParagraph>
        {{
          _t(
            'The image "%{name}" is referenced by %{count} map(s). Deleting it will leave those maps without an image. Continue?',
            { name: props.imageName, count: props.usage.length }
          )
        }}
      </CmkParagraph>
      <CmkLinkCardContainer>
        <CmkLinkCard
          v-for="entry in props.usage"
          :key="entry.map"
          icon-name="dashboard-main"
          :title="untranslated(entry.alias || entry.map)"
          :subtitle="usageSubtitle(entry)"
          :url="nav.href({ view: 'map', name: entry.map })"
          :open-in-new-tab="true"
        />
      </CmkLinkCardContainer>
      <div class="maps-image-usage-dialog__actions">
        <CmkButton variant="secondary" @click="emit('cancel')">{{ _t('Cancel') }}</CmkButton>
        <CmkButton variant="danger" @click="emit('confirm')">{{ _t('Delete') }}</CmkButton>
      </div>
    </div>
  </CmkSlideInDialog>
</template>

<style scoped>
.maps-image-usage-dialog {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-5);
  padding-bottom: var(--dimension-6);
  line-height: 1.5;
}

/* Stays reachable while a long usage list scrolls. */
.maps-image-usage-dialog__actions {
  position: sticky;
  bottom: 0;
  display: flex;
  justify-content: flex-end;
  gap: var(--dimension-3);
  padding-top: var(--dimension-4);
  background: var(--ux-theme-3);
  border-top: 1px solid var(--default-border-color);
}
</style>
