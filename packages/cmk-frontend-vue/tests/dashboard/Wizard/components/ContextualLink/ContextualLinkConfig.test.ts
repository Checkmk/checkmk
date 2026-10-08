/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { useProvideFilterDefinitions } from 'cmk-ui-library/components/filter'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { describe, expect, it } from 'vitest'
import { defineComponent, h } from 'vue'

import ContextualLinkConfig from '@/dashboard/components/Wizard/components/ContextualLink/ContextualLinkConfig.vue'
import type { ContextualLinkOptions } from '@/dashboard/components/Wizard/components/ContextualLink/contextualLink'
import { useContextualLink } from '@/dashboard/components/Wizard/components/ContextualLink/useContextualLink'
import type { HostStatisticsContent } from '@/dashboard/components/Wizard/types'

const HOST_STATISTICS_OPTIONS: ContextualLinkOptions = {
  modes: ['default', 'inherited', 'custom'],
  filters: ['siteopt', 'wato_folder', 'hoststate', 'opthostgroup'],
  single_infos: []
}

function renderConfig(
  options: ContextualLinkOptions = HOST_STATISTICS_OPTIONS,
  props: { defaultTarget?: TranslatedString } = {}
) {
  const handler = useContextualLink<HostStatisticsContent>(options, undefined)
  render(
    defineComponent({
      setup() {
        useProvideFilterDefinitions({ definitions: {}, groups: {} })
        return () => h(ContextualLinkConfig, { handler, ...props })
      }
    })
  )
  return handler
}

describe('ContextualLinkConfig', () => {
  it('names the built-in target in default mode', () => {
    renderConfig(HOST_STATISTICS_OPTIONS, { defaultTarget: untranslated('All hosts') })

    expect(screen.getByText('Target page')).toBeInTheDocument()
    expect(screen.getByText('All hosts')).toBeInTheDocument()
  })

  it('names no target page for a widget without a single built-in target', () => {
    renderConfig()

    expect(screen.getByText('Redirect to the default page defined by Checkmk.')).toBeInTheDocument()
    expect(screen.queryByText('Target page')).not.toBeInTheDocument()
  })
})
