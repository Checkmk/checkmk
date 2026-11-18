/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import { Response } from 'cmk-ui-library/components/CmkSuggestions'
import CmkLabelQueryBuilder from 'cmk-ui-library/components/filter/private/input/LabelGroups/LabelQueryBuilder.vue'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { expect, test } from 'vitest'

const LABELS = ['cmk/rmk/application:CRM', 'cmk/rmk/application:Shop', 'region:emea']

async function suggestLabels(query: string): Promise<Response> {
  return new Response(
    LABELS.filter((label) => label.includes(query)).map((label) => ({
      name: label,
      title: untranslated(label)
    }))
  )
}

async function selectFirstLabel(label: string): Promise<void> {
  await userEvent.click(screen.getByRole('combobox', { name: 'Label' }))
  await userEvent.click(await screen.findByRole('option', { name: label }))
}

test('suggests the labels of its source', async () => {
  render(CmkLabelQueryBuilder, { props: { suggestLabels } })

  await userEvent.click(screen.getByRole('combobox', { name: 'Label' }))

  expect(await screen.findByRole('option', { name: 'region:emea' })).toBeInTheDocument()
})

test('shows the selected label', async () => {
  render(CmkLabelQueryBuilder, { props: { suggestLabels } })

  await selectFirstLabel('region:emea')

  await waitFor(() =>
    expect(screen.getAllByRole('combobox', { name: 'Label' })[0]).toHaveTextContent('region:emea')
  )
})

test('does not suggest a label that another row of the group uses', async () => {
  render(CmkLabelQueryBuilder, { props: { suggestLabels } })
  await selectFirstLabel('region:emea')

  await userEvent.click(screen.getAllByRole('combobox', { name: 'Label' })[1]!)

  expect(
    await screen.findByRole('option', { name: 'cmk/rmk/application:Shop' })
  ).toBeInTheDocument()
  expect(screen.queryByRole('option', { name: 'region:emea' })).not.toBeInTheDocument()
})
