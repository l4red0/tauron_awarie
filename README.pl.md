# Tauron Awarie (Home Assistant)


Integracja informacji o wyłączeniach i awariach dla abonentów dostawcy energii Tauron.

![Calendar](./docs/calendar.png)

## Funkcje

- **Monitorowanie przerw w dostawie prądu**: Pobiera bieżące i planowane przerwy w dostawie prądu z API Tauron Dystrybucja co 12h dla danej lokalizacji
- **Filtrowanie oparte na lokalizacji**: Konfiguruj dla konkretnych miast, powiatów i gmin w Polsce
- **Integracja z kalendarzem**: Automatyczne tworzenie wydarzeń w kalendarzu dla planowanych przerw
- **Lokalizacja w języku polskim**: Pełna obsługa języka polskiego

## Instalacja

### HACS (zalecane)
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?repository=https%3A%2F%2Fgithub.com%2Fl4red0%2Ftauron_awarie&owner=l4red0&category=Integration)

1. Dodaj to repozytorium do HACS jako repozytorium niestandardowe
2. Wyszukaj „Tauron Awarie” w integracjach HACS
3. Zainstaluj i uruchom ponownie Home Assistant
4. Dodaj integrację za pomocą interfejsu użytkownika

### Instalacja ręczna

1. Skopiuj folder `custom_components/tauron_awarie` do katalogu `custom_components` w Home Assistant
2. Uruchom ponownie Home Assistant
3. Dodaj integrację za pomocą interfejsu użytkownika

## Konfiguracja

Integracja wykorzystuje Tauron WAAPI do pobierania danych o awariach. Konfiguracja obejmuje:

1. **Wybór miasta**: Wyszukaj i wybierz swoje miasto
2. **Wybór dzielnicy**: W przypadku miast z wieloma dzielnicami (np. Wrocław), wybierz konkretny obszar
3. **Integracja kalendarza**: Opcjonalnie włącz tworzenie wydarzeń w kalendarzu dla planowanych przerw w dostawie prądu

### Opcje konfiguracji

- **Wyszukiwanie miasta**: Wprowadź co najmniej 3 znaki, aby wyszukać polskie miasta
- **Ręczne wprowadzanie GAID**: Zaawansowana opcja ręcznego wprowadzania kodów GAID, jeśli automatyczne wyszukiwanie nie działa
- **Tworzenie kalendarza**: Odznacz, aby utworzyć wydarzenia w kalendarzu dla przerw w dostawie prądu

## Sensory

Integracja zapewnia sensor, który pokazuje:

- Dni do następnej planowanej awarii
- Szczegółowe informacje o awarii (czas rozpoczęcia, czas zakończenia, opis, typ)
- Listę wszystkich nadchodzących awarii
- Informacje o lokalizacji (województwo, powiat, gmina, miasto)

### Atrybuty sensora

- `next_start`: Znacznik czasu ISO rozpoczęcia następnej awarii
- `next_end`: Znacznik czasu ISO zakończenia następnej awarii
- `next_message`: Opis lokalizacji/szczegółów awarii
- `next_type`: Rodzaj awarii (Planowane/Awaryjne)
- `outage_count`: Łączna liczba nadchodzących awarii
- `outages`: Tablica wszystkich obiektów awarii

## Zdarzenia kalendarzowe

Po włączeniu integracji kalendarza, integracja tworzy zdarzenia czasowe dla planowanych przerw z:

- Podsumowanie: „Tauron [Typ] - [Nazwa miasta]”
- Opis: Awaria Szczegóły lokalizacji
- Godziny rozpoczęcia/zakończenia: Dokładny harmonogram przerw

> [!TIP]
> Możesz użyć dodatkowych integracji w HA aby w lepszy sposób zaprezentować dane na dashboardzie. Np. [hassio-trash-card](https://github.com/idaho/hassio-trash-card)

## Wymagania
- Home Assistant 2025.2.4 or later

## FAQ

* **Co zrobić jeśli mojego miasta nie ma na liście?**

Lokalna baza danych miast może być nie pełna. Jeśli Twojego miasta nie ma liście, możesz skorzystać opcji "Ręcznego dodawania GAID", która widoczna jest przy pierwszej konfiguracji oraz dodawaniu encji. Aby uzyskać odpowiednie GAID dla Twojego miejsca zamieszkania, musisz je wyciągnać z adresu url zaputania na stronie https://www.tauron-dystrybucja.pl/wylaczenia w sekcji "Sprawdź wyłączenia dla obszaru powiatu lub gminy".

* **Moim dostawcą prądu jest Energa. Co ze mną?**

Świetnie się składa, bo ta integracja powstała w oparciu o oryginalny pomysł @chauek, który stworzył taką [integrację informacji o awariach dla dostawcy Energa](https://github.com/chauek/energa_awarie).

* **Dodałem swoją miejscowość, ale żadna awaria czy przerwa nie dodała się do kalendarza. Dlaczego?**

Prawie na pewno oznacza to, że po prostu nie są planowane wyłączenia na najbliższe 7 dni. A także że nie ma miejsca aktualnie żadna awaria prądu.

* **Co ile Home Assistant aktualizuje informacje z API o wyłączeniach i awariach?**

W duchu poszanowania zasobów serwera Tauron Dystrybucja, aktualizacja odbywa się raz na 12h. Z tego samego powodu ta integracja ma także wbudowaną (dość obszerną) bazę specyficznych tylko dla Taurona identyfikatorów miejscowości.

## Wsparcie

- [GitHub Issues](https://github.com/l4red0/tauron_awarie/issues) do zgłaszania błędów i pomysłów
- [Home Assistant Community](https://community.home-assistant.io) ogólne forum Home Assistant niezwiązane z tą integracją

#### License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

#### Disclaimer

Ta integracja nie jest oficjalnie powiązana z Tauron Dystrybucja. Korzystasz na własne ryzyko. Autorzy nie ponoszą odpowiedzialności za jakiekolwiek szkody lub problemy spowodowane korzystaniem z tej integracji.
