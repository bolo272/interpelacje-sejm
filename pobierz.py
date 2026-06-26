"""Pobiera najnowsze odpowiedzi na interpelacje (Sejm, kadencja 10) i zapisuje
czytelny zrzut JSON do dane/raport-{data}.json oraz dane/najnowszy.json.

Filtruje przez modifiedSince = wczoraj 00:00, sortuje po -lastModified.
Dla każdej odpowiedzi dociąga treść: z HTML (body) albo z PDF (onlyAttachment).
"""
import datetime
import io
import json
import re
from html.parser import HTMLParser
from pathlib import Path

import pypdf
import requests

API = "https://api.sejm.gov.pl/sejm/term10/interpellations"


class _Tekst(HTMLParser):
    """Zbiera widoczny tekst z HTML, dodaje znaki nowej linii dla bloków."""

    BLOK = {"p", "div", "br", "h1", "h2", "h3", "h4", "li", "tr", "table"}

    def __init__(self) -> None:
        super().__init__()
        self.czesci: list[str] = []
        self._pomin = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._pomin += 1
        if tag in self.BLOK:
            self.czesci.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._pomin:
            self._pomin -= 1
        if tag in self.BLOK:
            self.czesci.append("\n")

    def handle_data(self, data):
        if not self._pomin:
            self.czesci.append(data)


def html_na_tekst(html: str) -> str:
    p = _Tekst()
    p.feed(html)
    txt = "".join(p.czesci)
    txt = re.sub(r"[ \t]+", " ", txt)
    txt = re.sub(r"\n[ \t]*\n[ \t]*\n+", "\n\n", txt)
    return txt.strip()


def pdf_na_tekst(content: bytes) -> str:
    reader = pypdf.PdfReader(io.BytesIO(content))
    return "\n".join((s.extract_text() or "") for s in reader.pages).strip()


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


def dodaj_tresc(rec: dict, sess: requests.Session) -> None:
    """Dopisuje rec['tresc'] i rec['tresc_zrodlo'].

    onlyAttachment -> tekst z PDF; w przeciwnym razie tekst z HTML body.
    Pojedynczy błąd nie przerywa całego zrzutu — zapisujemy go w polu.
    """
    if rec["tresc_tylko_w_pdf"]:
        teksty = []
        for pdf in rec["pdfy"]:
            try:
                r = sess.get(pdf["url"], timeout=60)
                r.raise_for_status()
                teksty.append(pdf_na_tekst(r.content))
            except Exception as e:  # noqa: BLE001
                teksty.append(f"[błąd PDF {pdf.get('nazwa')}: {e}]")
        tekst = "\n\n".join(t for t in teksty if t).strip()
        rec["tresc_zrodlo"] = "pdf" if tekst else "pdf-bez-tekstu"
        rec["tresc"] = tekst
    else:
        try:
            r = sess.get(rec["link_tresci"], timeout=60)
            r.raise_for_status()
            rec["tresc_zrodlo"] = "html"
            rec["tresc"] = html_na_tekst(r.text)
        except Exception as e:  # noqa: BLE001
            rec["tresc_zrodlo"] = f"błąd: {e}"
            rec["tresc"] = ""


def main() -> None:
    modified_since = wczoraj_polnoc()
    params = {"modifiedSince": modified_since, "sort_by": "-lastModified", "limit": 100}
    r = requests.get(API, params=params, timeout=30)
    r.raise_for_status()
    surowe = r.json()

    raport = [p for it in surowe if (p := przetworz(it)) is not None]

    with requests.Session() as sess:
        for rec in raport:
            dodaj_tresc(rec, sess)

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
