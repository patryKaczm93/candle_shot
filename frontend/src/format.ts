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

const priceFormat = new Intl.NumberFormat('pl-PL', { style: 'currency', currency: 'PLN' })

/** Grosze from the API → "49,00 zł". Display only; the backend owns all amounts. */
export function formatPrice(grosze: number): string {
  return priceFormat.format(grosze / 100)
}

export function candleCount(count: number): string {
  return `${count} ${pluralPl(count, ['świeczka', 'świeczki', 'świeczek'])}`
}
