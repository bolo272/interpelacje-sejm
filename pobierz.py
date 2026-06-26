"""Pobiera najnowsze odpowiedzi na interpelacje (Sejm, kadencja 10) i zapisuje
czytelny zrzut JSON do dane/raport-{data}.json oraz dane/najnowszy.json.

Filtruje przez modifiedSince = wczoraj 00:00, sortuje po -lastModified.
"""
import datetime
import json
from pathlib import Path

import requests

API = "https://api.sejm.gov.pl/sejm/term10/interpellations"


def wczoraj_polnoc() -> str:
    wczoraj = (datetime.datetime.now() - datetime.timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return wczoraj.strftime("%Y-%m-%dT%H:%M")


def link_body(reply: dict) -> str | None:
    for l in reply.get("links", []):
        if l.get("rel") == "body":
            return l.get("href")
    return None


def przetworz(item: dict) -> dict | None:
    replies = item.get("replies") or []
    if not replies:
        return None
    # najnowsza odpowiedz po lastModified
    reply = max(replies, key=lambda r: r.get("lastModified", ""))
    pdfy = [
        {"nazwa": a.get("name"), "url": a.get("URL")}
        for a in (reply.get("attachments") or [])
    ]
    return {
        "numer": item.get("num"),
        "tytul": item.get("title"),
        "adresat": item.get("to"),
        "autor_odpowiedzi": reply.get("from"),
        "data_odpowiedzi": reply.get("receiptDate"),
        "ostatnia_modyfikacja": reply.get("lastModified"),
        "tresc_tylko_w_pdf": bool(reply.get("onlyAttachment")),
        "link_tresci": link_body(reply),
        "pdfy": pdfy,
    }


def main() -> None:
    modified_since = wczoraj_polnoc()
    params = {"modifiedSince": modified_since, "sort_by": "-lastModified", "limit": 100}
    r = requests.get(API, params=params, timeout=30)
    r.raise_for_status()
    surowe = r.json()

    raport = [p for it in surowe if (p := przetworz(it)) is not None]

    wynik = {
        "pobrano": datetime.datetime.now().isoformat(timespec="seconds"),
        "modified_since": modified_since,
        "liczba_interpelacji": len(raport),
        "interpelacje": raport,
    }

    dane = Path("dane")
    dane.mkdir(exist_ok=True)
    dzis = datetime.date.today().isoformat()
    for sciezka in (dane / f"raport-{dzis}.json", dane / "najnowszy.json"):
        sciezka.write_text(
            json.dumps(wynik, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    print(f"Zapisano {len(raport)} interpelacji (z {len(surowe)} pobranych).")
    print(f"-> dane/raport-{dzis}.json oraz dane/najnowszy.json")


if __name__ == "__main__":
    main()
