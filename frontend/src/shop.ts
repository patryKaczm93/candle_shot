// Shop details shown to customers. TODO(9.3): fill in before launch.
export const CONTACT_EMAIL = '[adres e-mail]'

export function mailto(subject: string): string {
  return `mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent(subject)}`
}
