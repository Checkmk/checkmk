export const asStringArray = (value?: string[] | string): string[] => {
  if (!value) {
    return []
  }
  return Array.isArray(value) ? value : [value]
}
