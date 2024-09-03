import { fireEvent, render, screen } from '@testing-library/vue'
import FormCatalog from '@/form/components/forms/FormCatalog.vue'
import type {
  String as StringSpec,
  Dictionary as DictionarySpec,
  DictionaryElement,
  Catalog
} from '@/form/components/vue_formspec_components'
import { renderFormWithData } from '../cmk-form-helper'

type PartialExcept<T, K extends keyof T> = Pick<T, K> & Partial<Omit<T, K>>

function getStringFormspec(
  title: string,
  options?: Partial<Omit<DictionarySpec, 'type'>>
): StringSpec {
  return {
    type: 'string',
    title: title,
    help: `ut help ${title}`,
    validators: [],
    input_hint: `ut input hint ${title}`,
    ...options
  }
}

function getDictionaryFormspec(
  dictionaryOptions: Partial<Omit<DictionarySpec, 'type'>>,
  elements: Array<PartialExcept<Omit<DictionaryElement, 'type'>, 'ident' | 'parameter_form'>>
): DictionarySpec {
  return {
    type: 'dictionary',
    title: 'dictionary title',
    help: 'dictionary help',
    groups: [],
    layout: 'one_column',
    validators: [],
    elements: elements.map((element) => {
      return {
        required: false,
        default_value: '',
        ...element
      }
    }),
    ...dictionaryOptions
  }
}

function renderSimpleCatalog() {
  return render(FormCatalog, {
    props: {
      spec: {
        type: 'catalog',
        title: 'catalog title',
        help: 'catalog help',
        validators: [],
        topics: [
          {
            key: 'some_ut_key',
            dictionary: getDictionaryFormspec(
              {
                title: 'ut embedded dictionary title'
                // this title will be moved into the catalog and displayed there a stitle
              },
              [
                {
                  ident: 'ut_string_1',
                  parameter_form: getStringFormspec('title of string input')
                }
              ]
            )
          }
        ]
      },
      data: { some_ut_key: {} }, // TODO: some_ut_key is required. should it be?
      backendValidation: []
    }
  })
}

test('FormCatalog open/close topic', async () => {
  renderSimpleCatalog()

  // just make sure that the string input is rendered
  await screen.findByText('title of string input')

  const headline = await screen.findByText('ut embedded dictionary title')
  // the visibility of elements is changed via classes and css, but the css is not
  // available in the tests, so we have to manually check if the classes are added.
  // TODO: we should really change our code to make the following possible:
  // it should be quite easy to use v-show for that...
  // expect(title).not.toBeVisible()
  const parent = headline.parentElement!.parentElement!.parentElement!
  expect(parent).toHaveClass('open')
  expect(parent).not.toHaveClass('closed')

  await fireEvent.click(headline.parentElement!)
  expect(parent).not.toHaveClass('open')
  expect(parent).toHaveClass('closed')

  await fireEvent.click(headline.parentElement!)
  expect(parent).toHaveClass('open')
  expect(parent).not.toHaveClass('closed')
})

test('FormCatalog collapse/open all', async () => {
  renderSimpleCatalog()
  await screen.findByText('title of string input')

  const headline = await screen.findByText('ut embedded dictionary title')
  const parent = headline.parentElement!.parentElement!.parentElement!
  expect(parent).toHaveClass('open')
  expect(parent).not.toHaveClass('closed')

  await fireEvent.click(screen.getByText('Collapse all'))
  expect(parent).toHaveClass('closed')
  expect(parent).not.toHaveClass('open')

  await fireEvent.click(screen.getByText('Open all'))
  expect(parent).toHaveClass('open')
  expect(parent).not.toHaveClass('closed')
})

test('FormCatalog default value', async () => {
  function getDefinition(stringIdent: string) {
    return {
      spec: {
        type: 'catalog',
        title: 'catalog title',
        help: 'catalog help',
        validators: [],
        topics: [
          {
            key: 'some_ut_key',
            dictionary: getDictionaryFormspec(
              {
                title: 'ut embedded dictionary title'
                // this title will be moved into the catalog and displayed there a stitle
              },
              [
                {
                  ident: stringIdent,
                  parameter_form: getStringFormspec('title of string input'),
                  default_value: 'ut_string_1 default value'
                }
              ]
            )
          }
        ]
      } as Catalog,
      data: { some_ut_key: {} },
      backendValidation: []
    }
  }
  const { getCurrentData, rerender } = renderFormWithData(
    getDefinition('ut_string_1_ident_default')
  )

  // wait until everything is rendered:
  await screen.findByText('title of string input')

  expect(getCurrentData()).toBe(
    '{"some_ut_key":{"ut_string_1_ident_default":"ut_string_1 default value"}}'
  )

  vi.spyOn(console, 'warn').mockImplementation(() => {}) // TODO: this should be removed! it warns about a typing problem:
  // [Vue warn]: Invalid prop: type check failed for prop "data". Expected String with value "undefined", got Undefined
  await rerender(getDefinition('some_other_string_indent'))

  expect(getCurrentData()).toBe(
    '{"some_ut_key":{"some_other_string_indent":"ut_string_1 default value"}}'
  )
})
