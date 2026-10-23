<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkStateCountBar, { type StateSegment } from 'cmk-ui-library/components/CmkStateCountBar.vue'
import CmkTooltip, {
  CmkTooltipContent,
  CmkTooltipProvider,
  CmkTooltipTrigger
} from 'cmk-ui-library/components/CmkTooltip'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { onMounted, ref } from 'vue'

defineProps<{ screenshotMode: boolean }>()

const shown = ref(false)
onMounted(() => {
  shown.value = true
})

const segments: StateSegment[] = [
  { label: untranslated('OK'), count: 24, color: 'success' },
  { label: untranslated('WARN'), count: 3, color: 'warning' },
  { label: untranslated('CRIT'), count: 1, color: 'danger' },
  { label: untranslated('UNKNOWN'), count: 0, color: 'unknown' },
  { label: untranslated('PENDING'), count: 2, color: 'default' }
]
</script>

<template>
  <div>
    <section>
      <h3>Text: a one-line label</h3>
      <p>For example the absolute range of a time picker preset.</p>
      <div class="ucl-cmk-tooltip-dev__example">
        <CmkTooltipProvider>
          <CmkTooltip :open="shown">
            <CmkTooltipTrigger as-child>
              <CmkButton variant="secondary">Last 8 days</CmkButton>
            </CmkTooltipTrigger>
            <CmkTooltipContent side="right" variant="text">
              2026-03-20 - 2026-03-28
            </CmkTooltipContent>
          </CmkTooltip>
        </CmkTooltipProvider>
      </div>
    </section>

    <section>
      <h3>Content: title bar above a content area</h3>
      <p>Title left aligned in regular weight, optional text right aligned.</p>
      <div class="ucl-cmk-tooltip-dev__example ucl-cmk-tooltip-dev__example--content">
        <CmkTooltipProvider>
          <CmkTooltip :open="shown">
            <CmkTooltipTrigger as-child>
              <CmkButton variant="secondary">Service states</CmkButton>
            </CmkTooltipTrigger>
            <CmkTooltipContent
              side="right"
              variant="content"
              :title="untranslated('Fr, 2026-03-19')"
              :title-aside="untranslated('13:27:59')"
            >
              <CmkStateCountBar :segments="segments" />
            </CmkTooltipContent>
          </CmkTooltip>
        </CmkTooltipProvider>
      </div>
    </section>

    <section>
      <h3>Content: bold title</h3>
      <p>For example a graph preview titled with the graph name.</p>
      <div class="ucl-cmk-tooltip-dev__example ucl-cmk-tooltip-dev__example--content">
        <CmkTooltipProvider>
          <CmkTooltip :open="shown">
            <CmkTooltipTrigger as-child>
              <CmkButton variant="secondary">Graph preview</CmkButton>
            </CmkTooltipTrigger>
            <CmkTooltipContent
              side="right"
              variant="content"
              :title="untranslated('Graph title')"
              :title-aside="untranslated('Fr, 2026-03-19 13:27:59')"
              title-bold
            >
              <CmkStateCountBar :segments="segments" />
            </CmkTooltipContent>
          </CmkTooltip>
        </CmkTooltipProvider>
      </div>
    </section>

    <section>
      <h3>Content: centered title</h3>
      <p>A centered or right aligned title has no aside text.</p>
      <div class="ucl-cmk-tooltip-dev__example ucl-cmk-tooltip-dev__example--content">
        <CmkTooltipProvider>
          <CmkTooltip :open="shown">
            <CmkTooltipTrigger as-child>
              <CmkButton variant="secondary">Centered title</CmkButton>
            </CmkTooltipTrigger>
            <CmkTooltipContent
              side="right"
              variant="content"
              :title="untranslated('Graph title')"
              title-align="center"
            >
              <CmkStateCountBar :segments="segments" />
            </CmkTooltipContent>
          </CmkTooltip>
        </CmkTooltipProvider>
      </div>
    </section>

    <section>
      <h3>Content: without a title</h3>
      <p>The title bar is left out when neither a title nor an aside text is given.</p>
      <div class="ucl-cmk-tooltip-dev__example ucl-cmk-tooltip-dev__example--content">
        <CmkTooltipProvider>
          <CmkTooltip :open="shown">
            <CmkTooltipTrigger as-child>
              <CmkButton variant="secondary">Attributes</CmkButton>
            </CmkTooltipTrigger>
            <CmkTooltipContent side="right" variant="content">
              <CmkStateCountBar :segments="segments" />
            </CmkTooltipContent>
          </CmkTooltip>
        </CmkTooltipProvider>
      </div>
    </section>
  </div>
</template>

<style scoped>
.ucl-cmk-tooltip-dev__example {
  display: flex;
  align-items: center;
  min-height: 40px;
}

.ucl-cmk-tooltip-dev__example--content {
  min-height: 140px;
}
</style>
