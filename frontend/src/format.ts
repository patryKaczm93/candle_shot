/** Polish plural form: pluralPl(2, ['produkt', 'produkty', 'produktów']) → 'produkty'. */
export function pluralPl(count: number, [one, few, many]: [string, string, string]): string {
  if (count === 1) return one
  const lastDigit = count % 10
  const lastTwo = count % 100
  if (lastDigit >= 2 && lastDigit <= 4 && (lastTwo < 12 || lastTwo > 14)) return few
  return many
}

export function cartLabel(count: number): string {
  if (count === 0) return 'Koszyk, pusty'
  return `Koszyk, ${count} ${pluralPl(count, ['produkt', 'produkty', 'produktów'])}`
}
