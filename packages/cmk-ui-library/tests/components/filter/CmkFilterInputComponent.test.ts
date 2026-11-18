/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { CmkFilterInputComponent } from 'cmk-ui-library/components/filter'
import { restApiHttp, useMswServer } from 'cmk-ui-library/vitest.msw'
import { expect, test } from 'vitest'

const HOST_LABEL = 'os:linux'
const SERVICE_LABEL = 'app:shop'
const LABELS: Record<string, string[]> = { host: [HOST_LABEL], service: [SERVICE_LABEL] }

useMswServer(
  restApiHttp.post('/objects/autocomplete/{autocomplete_id}', async ({ request, response }) => {
    const { parameters = {} } = await request.json()
    const labels = LABELS[String(parameters['object_type'])] ?? Object.values(LABELS).flat()
    return response(200).json({ choices: labels.map((label) => ({ id: label, value: label })) })
  })
)

test.each([
  { objectType: 'host', suggested: HOST_LABEL, other: SERVICE_LABEL },
  { objectType: 'service', suggested: SERVICE_LABEL, other: HOST_LABEL }
] as const)(
  'the $objectType label filter suggests only $objectType labels',
  async ({ objectType, suggested, other }) => {
    render(CmkFilterInputComponent, {
      props: {
        component: {
          component_type: 'label_group',
          id: `${objectType}_labels`,
          object_type: objectType
        },
        configuredFilterValues: {
          [`${objectType}_labels_count`]: '1',
          [`${objectType}_labels_1_vs_count`]: '1'
        }
      }
    })

    await userEvent.click(screen.getByRole('combobox', { name: 'Label' }))

    expect(await screen.findByRole('option', { name: suggested })).toBeInTheDocument()
    expect(screen.queryByRole('option', { name: other })).not.toBeInTheDocument()
  }
)
