#!/usr/bin/env python3
"""
Fusiona tot el lloc "La Sexta Aumentada" en un únic fitxer HTML autònom.
Tots els recursos (imatges, SVG, àudio) s'incrusten com a data URIs base64,
de manera que el lloc funciona des d'un sol URL sense dependències externes.
"""

import base64
import mimetypes
import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE_DIR, "index.html")
OUT = os.path.join(BASE_DIR, "La-Sexta-Aumentada.html")

# Àudio: preferim la versió .mp3 (molt més lleugera) en lloc del .wav
AUDIO_PREFER_MP3 = True


def mime_for(path):
    mt, _ = mimetypes.guess_type(path)
    if mt is None:
        ext = os.path.splitext(path)[1].lower()
        mt = {
            ".svg": "image/svg+xml",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
        }.get(ext, "application/octet-stream")
    return mt


def resolve(rel_path):
    """Converteix una ruta relativa (des de l'arrel del projecte) a una ruta del sistema."""
    # Les rutes al HTML són relatives a l'arrel del projecte (ex: "Imagenes/...").
    return os.path.join(BASE_DIR, rel_path)


def embed(rel_path):
    """Retorna el data URI base64 per a la ruta relativa, amb substitució wav->mp3 si cal."""
    path = resolve(rel_path)

    # Substituir àudio wav per mp3 per reduir mida
    if AUDIO_PREFER_MP3 and rel_path.lower().endswith(".wav"):
        mp3 = os.path.splitext(path)[0] + ".mp3"
        if os.path.exists(mp3):
            path = mp3
            rel_path = os.path.splitext(rel_path)[0] + ".mp3"

    if not os.path.exists(path):
        print(f"  [AVÍS] No s'ha trobat: {rel_path}")
        return None

    with open(path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode("ascii")
    mt = mime_for(path)
    size_kb = len(data) / 1024
    print(f"  [OK] {rel_path} -> {mt} ({size_kb:.1f} KB)")
    return f"data:{mt};base64,{b64}"


def main():
    with open(SRC, "r", encoding="utf-8") as f:
        html = f.read()

    # Trobar totes les referències a recursos d'Imagenes (i subcarpetes).
    # Coincidim: src="...", url('...'), url("..."), url(...)
    # Els camins poden contenir espais (ex: "Imagenes/Sons Sisenes Aumentades/...").
    patterns = [
        re.compile(r'(src\s*=\s*["\'])(Imagenes/[^"\']+)(["\'])', re.IGNORECASE),
        re.compile(r'(data-audio\s*=\s*["\'])(Imagenes/[^"\']+)(["\'])', re.IGNORECASE),
        re.compile(r'(url\(\s*["\']?)(Imagenes/[^"\')\s]+)(["\']?\s*\))', re.IGNORECASE),
        # Imatges absolutes del domini (og:image, twitter:image) -> incrustar també
        # Substituïm l'URL completa (inclòs el domini) pel data URI.
        re.compile(r'https://www\.lasextaaumentada\.com/(Imagenes/[^"\']+)', re.IGNORECASE),
    ]

    n = 0
    new_html = html

    def make_repl(pre_group, path_group, post_group):
        def repl(m):
            rel = m.group(path_group)
            data_uri = embed(rel)
            if data_uri is None:
                return m.group(0)
            return data_uri
        return repl

    # La 4a patró només té 1 grup (la ruta); gestionem-la per separat.
    abs_pattern = patterns.pop()  # últim patró (URL absoluta)
    new_html, count = abs_pattern.subn(
        lambda m: (embed(m.group(1)) or m.group(0)), new_html
    )
    n += count

    for i, pat in enumerate(patterns):
        new_html, count = pat.subn(make_repl(1, 2, 3), new_html)
        n += count

    print(f"\nS'han incrustat {n} recursos.")

    # Comprovació: no hauria de quedar cap referència externa a Imagenes/
    leftover = re.findall(r'Imagenes/[^"\')\s]+', new_html)
    if leftover:
        print(f"[AVÍS] Queden {len(leftover)} referències no resoltes:")
        for l in set(leftover):
            print("   -", l)
    else:
        print("[OK] Cap referència externa a 'Imagenes/' restant.")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(new_html)

    total = os.path.getsize(OUT) / (1024 * 1024)
    print(f"\nFitxer generat: {OUT}")
    print(f"Mida total: {total:.2f} MB")


if __name__ == "__main__":
    main()