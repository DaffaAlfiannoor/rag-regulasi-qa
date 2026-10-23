"""Tanya lewat terminal.

Contoh:
    python ask.py "Apa saja hak subjek data pribadi?" --k 4
"""
import argparse

import rag_core as rc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--k", type=int, default=4)
    ap.add_argument("--collection", default=rc.DEFAULT_COLLECTION)
    args = ap.parse_args()

    out = rc.answer(args.question, args.collection, args.k)
    print(f"\nJAWABAN ({out['mode']}):\n{out['answer']}\n")
    print("SUMBER:")
    for h in out["sources"]:
        label = f"Pasal {h['pasal']}" if h["pasal"] else h["source"]
        print(f"- {label} (distance={h['distance']:.3f})")


if __name__ == "__main__":
    main()
