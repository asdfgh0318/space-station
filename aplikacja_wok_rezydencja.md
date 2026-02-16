# Aplikacja na rezydencję WOK Warszawa 2026
## Temat przewodni: EKSPERYMENT

**Zespół:** Adam, Stas, Maksym (@dontriskit)
**Projekt:** Radioteleskop DIY + system neonów reaktywnych na dane SDR

---

## Tekst kuratorski (kontekst)

> Tegorocznym hasłem przewodnim jest eksperyment. To właśnie przestrzeń spokojnej pracy, nieśpiesznej eksploracji własnych pomysłów, taka, która sprzyja podążaniu za ciekawością, wydaje nam się dziś szczególnym luksusem. Eksperymentowanie wymaga namysłu, w niektórych wypadkach implikuje doświadczenia zmysłowe, w innych – ich brak. W każdym wypadku z eksperymentem wiąże się ryzyko nierozpoznania, bycia niezrozumianym, zdezinterpretowaną. Podczas eksperymentowania w WOK osoby twórcze będą mogły w możliwie bezpiecznej przestrzeni prototypować, testować pomysły i rozwiązania oraz swobodnie podążać za własnym procesem. To, co zostaje po eksperymentowaniu z eksperymentem, nie jest produktem, nie podlega logice utowarowienia, lecz pozostaje świadectwem trajektorii…

---

## 1. Jak rozumiecie temat tegorocznej edycji rezydencji?
*(maksymalnie 1800 znaków ze spacjami)*

Eksperyment to słowo, które jednakowo silnie rezonuje w laboratorium i w pracowni. W nauce to kontrolowana procedura – hipoteza, pomiar, weryfikacja. W sztuce to gest otwarcia na niewiadome. Nasz projekt lokuje się dokładnie na tym przecięciu i czerpie z obu tradycji, nie przynależąc w pełni do żadnej.

Budujemy radioteleskop – urządzenie do odbioru fal elektromagnetycznych z kosmosu. To dosłowny eksperyment: nie wiemy, co usłyszymy. Fale radiowe są niewidoczne, niesłyszalne, niewyczuwalne bez pośrednictwa technologii. Eksperymentujemy więc z samym aktem percepcji – rozszerzamy ludzkie zmysły za pomocą anteny, odbiornika SDR i kodu, próbując uchwycić to, co jest obecne wokół nas, ale niedostępne. Tekst kuratorski mówi o doświadczeniach zmysłowych i ich braku – nasz projekt żyje właśnie w tej szczelinie: czynimy słyszalnym to, co z natury jest nieme.

Eksperymentujemy też z materialnością i ekonomią narzędzi. Teleskop jest drukowany 3D z recyklingowanych części, za budżet poniżej 200 euro. Testujemy, czy narzędzia obserwacji kosmosu mogą istnieć poza instytucjami dysponującymi dużymi środkami – demokratyzacja nasłuchu jako praktyka twórcza. Pracujemy w trójkę, łącząc programowanie, elektronikę i rzeźbę świetlną – sam ten układ jest eksperymentem w kolaboracji.

System neonów, przekształcający dane radiowe w pulsacje światła, jest eksperymentem translacji – próbą nadania widzialnej, cielesnej formy temu, co niezmysłowe. Ryzykujemy niezrozumienie: czy to nauka? Czy sztuka? Ale właśnie ta nieokreśloność, ta przestrzeń między dyscyplinami, jest naszym miejscem pracy. Eksperyment rozumiemy jako prawo do procesu bez gwarancji produktu – do podążania za sygnałem, dosłownie i metaforycznie, bez pewności, dokąd nas zaprowadzi.

---

## 2. Koncepcja na proces rezydencyjny
*(maksymalnie 1800 znaków ze spacjami)*

Nasz proces rezydencyjny składa się z trzech splecionych ścieżek, które zbiegają się w instalację – otwartą stację nasłuchową. Pracujemy jako trio – każdy wnosi odmienną wrażliwość i kompetencję, a proces wzajemnego uczenia się jest częścią eksperymentu.

Pierwsza ścieżka: budowa. Drukujemy 3D elementy mechaniczne trackera antenowego, montujemy obrotowe mocowanie na osi azymutu i elewacji, kalibrujemy system automatycznego śledzenia obiektów na niebie. Pracujemy z otwartym kodem, drukarką Ender 3 i odbiornikiem RTL-SDR podłączonym do Raspberry Pi. To proces z natury powolny – każdy wydruk trwa godziny, kalibracja wymaga powtarzalnych, cierpliwych prób. Czas druku staje się czasem namysłu i rozmowy.

Druga ścieżka: translacja. Stas buduje system neonowych lamp reagujących na strumień danych z odbiornika SDR w czasie rzeczywistym. Sygnały satelitów meteorologicznych, emisja wodoru na częstotliwości 1420 MHz, kosmiczny szum tła – zostają przełożone na pulsacje, rytmy i natężenie światła. Nie w logice precyzyjnej wizualizacji danych, lecz bliżej synestezji – neon jako zmysł, którego nam brakuje, organ percepcji radiowej.

Trzecia ścieżka: nasłuch. Regularne sesje obserwacyjne, podczas których kierujemy antenę w różne obszary nieba i słuchamy. Sesje są otwarte – zapraszamy współrezydentów i odwiedzających. Nie obiecujemy odkrycia. Obiecujemy uważność wobec sygnałów, które docierają do nas nieustannie, niezależnie od tego, czy ktokolwiek ich słucha.

Po rezydencji pozostanie działająca stacja, archiwum sesji i otwarty kod – zapis trajektorii eksperymentu. Wszystko publikujemy open source, zapraszając innych do kontynuacji i modyfikacji. Eksperyment nie kończy się z rezydencją – rozgałęzia się, staje się wspólny, wymyka się autorom.

---

## Notatki robocze

### Kluczowe motywy do podkreślenia:
- **Nieśpieszność** – druk 3D = godziny czekania, kalibracja = powtarzalność, nasłuch = cierpliwość
- **Ryzyko niezrozumienia** – projekt na granicy sztuki i nauki, żadna strona nie "uznaje" w pełni
- **Nie-produkt** – stacja nasłuchowa to proces, nie obiekt; dane płyną, neony pulsują, nic nie jest "skończone"
- **Demokratyzacja** – <200 EUR, open source, drukarka za 800 zł
- **Zmysłowość / jej brak** – fale radiowe → neon = czynienie niewidzialnego widzialnym
- **Trajektoria** – archiwum sesji jako zapis drogi, nie celu

### Elementy techniczne projektu:
- Radioteleskop: RPi 4 + RTL-SDR, PETG 3D print, belt-driven alt-az mount
- Pasma: VHF (137 MHz weather sats), L-band (1420 MHz hydrogen), Ku-band (12.2 GHz masers)
- System neonów: dane SDR → przetwarzanie → sterowanie jasnością/pulsacją neonów
- Całość open source na GitHub
