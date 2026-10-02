<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { SimpleIcons } from 'cmk-ui-library/components/CmkIcon'
import { getIconPath } from 'cmk-ui-library/components/CmkIcon/utils'
import CmkPointerTooltip, {
  type CmkPointerTooltipPointer
} from 'cmk-ui-library/components/CmkPointerTooltip.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { useTheme } from 'cmk-ui-library/lib/useTheme'
import { computed, ref } from 'vue'

import ContextualLinkTrigger from '@/dashboard/components/ContextualLinkTrigger.vue'
import type {
  SiteOverviewContent,
  SiteOverviewSites,
  VisualContext
} from '@/dashboard/types/widget'

import FigureTooltip, { type FigureTooltipContent } from './lib/FigureTooltip.vue'
import StateRingsHexagon from './lib/StateRingsHexagon.vue'
import { HEXAGON_MAX_BOX_WIDTH, STATE_HEXAGON_STYLE, hexagonGrid, hexagonPath } from './lib/hexagon'

const props = defineProps<{
  value: SiteOverviewSites
  width: number
  height: number
  hexagonSize: SiteOverviewContent['hexagon_size']
  filters: VisualContext
  interactive: boolean
}>()

const { _t, _tnp } = usei18n()
const { theme } = useTheme()

type SiteElement = SiteOverviewSites['sites'][number]
type SitePart = Extract<SiteElement, { status: 'online' }>['parts'][number]

const SITE_PART_TEXT: Record<SitePart['category'], (count: number) => string> = {
  critical: (count) =>
    _tnp(
      'site overview',
      'host is down or has critical services',
      'hosts are down or have critical services',
      count
    ),
  unknown: (count) =>
    _tnp(
      'site overview',
      'host is unreachable or has unknown services',
      'hosts are unreachable or have unknown services',
      count
    ),
  warning: (count) =>
    _tnp(
      'site overview',
      'host is UP but has services in WARNING state',
      'hosts are UP but have services in WARNING state',
      count
    ),
  downtime: (count) =>
    _tnp(
      'site overview',
      'host is in scheduled downtime',
      'hosts are in scheduled downtime',
      count
    ),
  ok: (count) =>
    _tnp(
      'site overview',
      'host is up and has no service problems',
      'hosts are up and have no service problems',
      count
    )
}

type OfflineStatus = Exclude<SiteElement['status'], 'online'>

const OFFLINE_SITE: Record<OfflineStatus, { text: string; icon: SimpleIcons }> = {
  disabled: { text: _t('The connection to this site has been disabled.'), icon: 'site-disabled' },
  down: { text: _t('This site is currently down.'), icon: 'site-down' },
  unreach: { text: _t('This site is currently not reachable.'), icon: 'site-unreach' },
  dead: { text: _t('This site is not responding.'), icon: 'site-dead' },
  waiting: {
    text: _t('The status of this site has not yet been determined.'),
    icon: 'site-waiting'
  },
  missing: { text: _t('This site does not exist.'), icon: 'site-missing' },
  unknown: { text: _t('The status of this site could not be determined.'), icon: 'site-missing' }
}

const FIGURE_LABEL = _t('Site overview')

function total(site: SiteElement): number {
  return site.status === 'online' ? site.parts.reduce((sum, part) => sum + part.count, 0) : 0
}

const shapes = computed(() => {
  const grid = hexagonGrid(props.value.sites.length, props.width, props.height, {
    layout: 'sites',
    maxBoxWidth: HEXAGON_MAX_BOX_WIDTH[props.hexagonSize]
  })
  if (grid === null) {
    return []
  }
  const largest = Math.max(0, ...props.value.sites.map(total))
  return props.value.sites.map((site, index) => {
    const center = grid.centers[index]!
    const base = {
      site,
      transform: `translate(${center.x}, ${center.y})`,
      hitPath: hexagonPath(grid.radius),
      label:
        grid.labelHeight === null
          ? null
          : { y: grid.radius + 4, width: grid.boxWidth, height: grid.labelHeight }
    }
    if (site.status !== 'online') {
      return { ...base, rings: null, iconPath: hexagonPath(grid.radius * 0.5) }
    }
    const scale = largest === 0 ? 0.5 : Math.max(0.5, Math.pow(total(site) / largest, 0.3))
    return {
      ...base,
      iconPath: null,
      rings: { parts: [...site.parts].reverse(), radius: grid.radius * scale }
    }
  })
})

const hovered = ref<{ site: SiteElement; pointer: CmkPointerTooltipPointer } | null>(null)

function hover(site: SiteElement, event: PointerEvent): void {
  hovered.value = { site, pointer: { clientX: event.clientX, clientY: event.clientY } }
}

const tooltip = computed<FigureTooltipContent | null>(() => {
  const site = hovered.value?.site
  if (site === undefined) {
    return null
  }
  if (site.status !== 'online') {
    return { title: site.alias, state: OFFLINE_SITE[site.status].text, rows: [] }
  }
  const count = total(site)
  return {
    title: site.alias,
    state: null,
    rows: [
      ...site.parts.map((part) => ({
        key: part.category,
        count: part.count,
        color: STATE_HEXAGON_STYLE[part.category].color,
        text: SITE_PART_TEXT[part.category](part.count)
      })),
      {
        key: 'total',
        count,
        color: 'transparent',
        text: _tnp('site overview', 'host in total', 'hosts in total', count)
      }
    ]
  }
})
</script>

<template>
  <svg
    role="figure"
    class="db-cmk-site-overview-sites-figure"
    :aria-label="FIGURE_LABEL"
    :width="width"
    :height="height"
    :viewBox="`0 0 ${width} ${height}`"
  >
    <g
      v-for="shape in shapes"
      :key="shape.site.site_id"
      :transform="shape.transform"
      @pointermove="hover(shape.site, $event)"
      @pointerleave="hovered = null"
    >
      <ContextualLinkTrigger
        v-if="shape.site.status === 'online'"
        :links="value.links"
        :link-properties="shape.site.link_properties"
        :filters="filters"
        :interactive="interactive"
      >
        <g :aria-label="shape.site.alias">
          <path :d="shape.hitPath" fill="transparent" />
          <StateRingsHexagon
            v-if="shape.rings"
            :parts="shape.rings.parts"
            :radius="shape.rings.radius"
            :ring-label="null"
          />
        </g>
      </ContextualLinkTrigger>
      <g v-else :aria-label="shape.site.alias">
        <path :d="shape.iconPath ?? ''" class="db-cmk-site-overview-sites-figure__offline" />
        <image
          :href="getIconPath(OFFLINE_SITE[shape.site.status].icon, theme)"
          x="-12"
          y="-12"
          width="24"
          height="24"
        />
      </g>
      <foreignObject
        v-if="shape.label"
        :x="-shape.label.width / 2"
        :y="shape.label.y"
        :width="shape.label.width"
        :height="shape.label.height + 4"
      >
        <div
          class="db-cmk-site-overview-sites-figure__label"
          :style="{ fontSize: `${shape.label.height}px` }"
        >
          {{ shape.site.alias }}
        </div>
      </foreignObject>
    </g>
  </svg>
  <CmkPointerTooltip :pointer="hovered?.pointer ?? null" @dismiss="hovered = null">
    <FigureTooltip v-if="tooltip" v-bind="tooltip" />
  </CmkPointerTooltip>
</template>

<style scoped>
.db-cmk-site-overview-sites-figure {
  --db-cmk-site-overview-sites-figure-headline: var(--ux-theme-4);

  display: block;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
[data-theme='modern-dark'] .db-cmk-site-overview-sites-figure {
  --db-cmk-site-overview-sites-figure-headline: var(--ux-theme-3);
}

.db-cmk-site-overview-sites-figure__offline {
  fill: var(--db-cmk-site-overview-sites-figure-headline);
  stroke: rgb(68 68 68);
  stroke-dasharray: 3, 3;
}

.db-cmk-site-overview-sites-figure__label {
  overflow: hidden;
  color: var(--font-color);
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
