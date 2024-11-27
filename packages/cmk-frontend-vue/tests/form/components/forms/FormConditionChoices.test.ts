/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import type * as FormSpec from '@/form/components/vue_formspec_components'
import FormConditionChoices from '@/form/components/forms/form_condition_choices'

const validators: FormSpec.Validator[] = [
  {
    type: 'length_in_range',
    min_value: 1,
    max_value: null,
    error_message: 'Please add at least one condition'
  }
]

const spec: FormSpec.ConditionChoices = {
  type: 'condition_choices',
  title: 'fooTitle',
  help: 'fooHelp',
  validators: validators,
  condition_groups: {
    group1: {
      title: 'Group 1',
      conditions: [
        { name: 'condition1', title: 'Condition 1' },
        { name: 'condition2', title: 'Condition 2' }
      ]
    }
  },
  i18n: {
    add_condition_label: 'add condition',
    select_condition_group_to_add: 'select group',
    no_more_condition_groups_to_add: 'no more groups',
    eq_operator: 'is',
    ne_operator: 'is not',
    or_operator: 'any of',
    nor_operator: 'none of'
  }
}

test('FormConditionChoices shows backendValidation', async () => {
  render(FormConditionChoices, {
    props: {
      spec,
      data: [],
      backendValidation: [
        {
          location: [],
          message: 'some message',
          invalid_value: [
            {
              group_name: 'group1',
              value: { oper_eq: 'condition1' }
            }
          ]
        }
      ]
    }
  })

  screen.getByText('some message')
  screen.getByText('Condition 1')
})

test('FormConditionChoices checks validators', async () => {
  render(FormConditionChoices, {
    props: {
      spec,
      data: [
        {
          group_name: 'group1',
          value: { oper_eq: 'condition1' }
        }
      ],
      backendValidation: []
    }
  })

  const deleteButton = screen.getByRole<HTMLButtonElement>('button')
  await fireEvent.click(deleteButton)

  screen.getByText('Please add at least one condition')
})
