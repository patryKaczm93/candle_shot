import { CONTACT_EMAIL } from '../shop'
import { LegalPage } from './LegalPage'

export function DeliveryReturnsPage() {
  return (
    <LegalPage title="Dostawa i zwroty">
      <h2>Dostawa</h2>
      <ul>
        <li>Paczkomat InPost: [cena] zł.</li>
        <li>Kurier: [cena] zł.</li>
        <li>Darmowa dostawa od [kwota] zł.</li>
        <li>Wysyłamy w [X] dni roboczych od zaksięgowania płatności.</li>
      </ul>
      <h2>Odstąpienie od umowy</h2>
      <p>
        Masz 14 dni na odstąpienie od umowy bez podania przyczyny, licząc od dnia otrzymania paczki. Wystarczy, że
        napiszesz do nas na {CONTACT_EMAIL} przed upływem tego terminu.
      </p>
      <p>
        Odeślij świeczkę na adres [adres do zwrotów] w ciągu 14 dni od odstąpienia. Zwrócimy pieniądze tą samą metodą
        płatności w ciągu 14 dni od otrzymania Twojego oświadczenia. [Kto pokrywa koszt odesłania.]
      </p>
      <h2>Reklamacje</h2>
      <p>
        Jeśli świeczka dotrze uszkodzona albo ma wadę, napisz na {CONTACT_EMAIL} i dołącz zdjęcie. Odpowiemy w ciągu 14
        dni.
      </p>
    </LegalPage>
  )
}

export function TermsPage() {
  return (
    <LegalPage title="Regulamin">
      <h2>1. Sprzedawca</h2>
      <p>[Nazwa firmy], [adres], NIP [NIP], e-mail: {CONTACT_EMAIL}.</p>
      <h2>2. Zamówienia</h2>
      <p>[Jak złożyć zamówienie, kiedy umowa zostaje zawarta.]</p>
      <h2>3. Ceny i płatności</h2>
      <p>
        Ceny podajemy w złotych i zawierają podatek VAT. Płacisz BLIKIEM, Przelewy24 lub kartą na bezpiecznej stronie
        Stripe. [Termin płatności.]
      </p>
      <h2>4. Dostawa</h2>
      <p>[Sposoby i koszty dostawy, czas realizacji.]</p>
      <h2>5. Odstąpienie od umowy</h2>
      <p>[Zasady odstąpienia, wyjątki, np. produkty na zamówienie.]</p>
      <h2>6. Reklamacje</h2>
      <p>[Tryb i terminy reklamacji.]</p>
      <h2>7. Postanowienia końcowe</h2>
      <p>[Prawo właściwe, pozasądowe rozwiązywanie sporów, data wejścia w życie.]</p>
    </LegalPage>
  )
}

export function PrivacyPage() {
  return (
    <LegalPage title="Polityka prywatności">
      <h2>1. Administrator danych</h2>
      <p>[Nazwa firmy], [adres], e-mail: {CONTACT_EMAIL}.</p>
      <h2>2. Jakie dane zbieramy</h2>
      <p>
        Przy zamówieniu: imię i nazwisko, e-mail, telefon, adres dostawy lub numer Paczkomatu, a przy fakturze NIP i
        nazwę firmy. Danych karty nie widzimy: płatności obsługuje Stripe.
      </p>
      <h2>3. W jakim celu</h2>
      <p>[Realizacja zamówienia, rozliczenia księgowe, obsługa reklamacji; podstawy prawne.]</p>
      <h2>4. Komu przekazujemy dane</h2>
      <p>[Stripe (płatności), InPost lub kurier (dostawa), dostawca poczty e-mail, hosting.]</p>
      <h2>5. Jak długo przechowujemy dane</h2>
      <p>[Okresy przechowywania.]</p>
      <h2>6. Twoje prawa</h2>
      <p>[Dostęp, sprostowanie, usunięcie, sprzeciw, skarga do Prezesa UODO.]</p>
      <h2>7. Pliki cookies i pamięć przeglądarki</h2>
      <p>
        Koszyk zapisujemy w pamięci Twojej przeglądarki (localStorage), żeby nie zniknął po odświeżeniu strony. Fonty
        ładujemy z naszego serwera, bez usług Google. [Inne narzędzia, jeśli zostaną dodane.]
      </p>
    </LegalPage>
  )
}
