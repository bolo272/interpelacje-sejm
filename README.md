# Codzienny zrzut odpowiedzi na interpelacje (Sejm, kadencja 10)

Dzienny cron pobiera z API Sejmu najnowsze odpowiedzi na interpelacje
i zapisuje czytelny zrzut JSON do katalogu `dane/`.

## Gdzie szukać zrzutu

- `dane/najnowszy.json` — zawsze ostatni zrzut (stały adres).
- `dane/raport-{RRRR-MM-DD}.json` — zrzut z danego dnia (archiwum).

Każdy zrzut zawiera listę interpelacji, a dla każdej: numer, tytuł, adresata,
autora odpowiedzi, datę, link do treści odpowiedzi oraz linki do PDF-ów.
Pole `tresc_tylko_w_pdf: true` oznacza, że treść jest wyłącznie w załączniku PDF.

## Jak odpalić ręcznie

**W GitHubie:** zakładka **Actions** → workflow **„Codzienny zrzut interpelacji"**
→ przycisk **Run workflow** (to `workflow_dispatch`). Workflow sam pobierze dane
i zacommituje zmiany w `dane/`.

**Lokalnie:**

```bash
pip install requests
python pobierz.py
```

## Harmonogram

Cron uruchamia się raz dziennie o **05:00 UTC** (~07:00 czasu polskiego latem,
06:00 zimą). Okno pobierania to wszystko zmodyfikowane od wczoraj 00:00.

> Uwaga: `limit=100` na zapytanie. W bardzo ruchliwym dniu może to uciąć część
> najstarszych modyfikacji z okna — paginacji celowo nie ma (prototyp).
