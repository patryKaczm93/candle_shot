import { Field } from './Field'

type LockerPickerProps = {
  id: string
  /** Paczkomat code, e.g. WAW01M; this is what POST /api/checkout receives as `locker_id`. */
  value: string
  onChange: (lockerId: string) => void
  error?: string
}

const FIND_LOCKER_URL = 'https://inpost.pl/znajdz-paczkomat'

/**
 * Choice of an InPost Paczkomat. For now the customer types the code.
 *
 * Plugging in the map (InPost Geowidget) only changes this file: keep the props, render the
 * widget (button „Wybierz na mapie” + chosen point, as in the mockup) and call
 * `onChange(point.name)` from its point-selected event. The form, validation and API stay as they are.
 */
export function LockerPicker({ id, value, onChange, error }: LockerPickerProps) {
  return (
    <Field
      id={id}
      label="Kod Paczkomatu"
      placeholder="np. WAW01M"
      autoComplete="off"
      autoCapitalize="characters"
      spellCheck={false}
      maxLength={20}
      value={value}
      onChange={(event) => onChange(event.target.value.toUpperCase())}
      error={error}
      hint={
        <>
          Kod znajdziesz na{' '}
          <a href={FIND_LOCKER_URL} target="_blank" rel="noopener noreferrer">
            mapie Paczkomatów InPost
          </a>
          .
        </>
      }
    />
  )
}
