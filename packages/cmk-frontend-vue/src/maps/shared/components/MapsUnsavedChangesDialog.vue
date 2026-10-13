<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkPopupDialog from 'cmk-ui-library/components/CmkPopupDialog.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, nextTick, ref, watch } from 'vue'

const { _t } = usei18n()

const props = defineProps<{ open: boolean }>()
defineEmits<{ confirm: []; cancel: [] }>()

const title = computed(() => _t('Discard unsaved changes?'))
const message = computed(() =>
  _t('You have unsaved changes on this page. Leaving now will discard them.')
)
const discardLabel = computed(() => _t('Discard changes'))
const stayLabel = computed(() => _t('Stay on page'))

// Pre-select the safe action so Enter dismisses the dialog instead of
// destroying work. CmkPopup disables reka-ui's auto-focus, so the focus
// must be set explicitly after the portal has rendered.
const stayBtnRef = ref<{ $el: HTMLElement } | null>(null)

watch(
  () => props.open,
  async (isOpen) => {
    if (!isOpen) {
      return
    }
    // CmkPopup focuses its own DialogContent in a `nextTick` after the
    // portal mounts. Wait two ticks so our explicit focus overrides it.
    await nextTick()
    await nextTick()
    stayBtnRef.value?.$el?.focus()
  }
)
</script>

<template>
  <CmkPopupDialog :open="open" icon="warning" :title="title" @close="$emit('cancel')">
    <CmkParagraph class="maps-unsaved-changes-dialog__message">{{ message }}</CmkParagraph>
    <div class="maps-unsaved-changes-dialog__actions">
      <CmkButton ref="stayBtnRef" variant="optional" @click="$emit('cancel')">
        {{ stayLabel }}
      </CmkButton>
      <CmkButton variant="secondary" @click="$emit('confirm')">
        {{ discardLabel }}
      </CmkButton>
    </div>
  </CmkPopupDialog>
</template>

<style scoped>
.maps-unsaved-changes-dialog__message {
  margin-bottom: var(--dimension-6);
}

.maps-unsaved-changes-dialog__actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--dimension-3);
}
</style>

<style>
/* The dialog is asked for from inside a slide-in, and both share the modal
   stacking level. If the slide-in is reopened after the attempt to close it
   (the map-view picker does that), it lands in the DOM behind the popup portal
   that just mounted, where an equal z-index is no longer enough — so the
   discard dialog is lifted explicitly.

   The block has to be unscoped: CmkPopup portals to the body and passes no
   class of ours through. That puts it in the shared bundle on every GUI page,
   which is why the :has narrows it to exactly the time this dialog is
   mounted. */
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
body:has(.cmk-slide-in__container):has(.maps-unsaved-changes-dialog__actions) .cmk-popup__container,
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
body:has(.cmk-slide-in__container):has(.maps-unsaved-changes-dialog__actions) .cmk-popup__overlay {
  z-index: calc(var(--z-index-modal) + 10);
}
</style>
