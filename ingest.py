"""Bangun index vektor dari PDF di folder data/.

Contoh:
    python ingest.py
    python ingest.py --chunk-size 800 --overlap 120
"""
import argparse
from pathlib import Path

import rag_core as rc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", nargs="+", help="Path PDF (default: semua PDF di data/)")
    ap.add_argument("--collection", default=rc.DEFAULT_COLLECTION)
    ap.add_argument("--chunk-size", type=int, default=1000, help="Ukuran chunk dalam karakter")
    ap.add_argument("--overlap", type=int, default=150)
    args = ap.parse_args()

    pdfs = args.pdf or sorted(str(p) for p in Path("data").glob("*.pdf"))
    if not pdfs:
        raise SystemExit("Taruh minimal satu PDF di folder data/ dulu.")
    n = rc.build_index(pdfs, args.collection, args.chunk_size, args.overlap)
    print(f"Selesai: {n} chunk dari {len(pdfs)} file masuk ke collection '{args.collection}'.")


if __name__ == "__main__":
    main()
