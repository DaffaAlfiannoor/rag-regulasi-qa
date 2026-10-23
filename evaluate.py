"""Evaluasi retrieval (dan opsional jawaban LLM) di beberapa konfigurasi.

Contoh:
    python evaluate.py
    python evaluate.py --chunk-sizes 500 1000 1500 --ks 1 3 5
    python evaluate.py --with-llm
"""
import argparse
from pathlib import Path

import pandas as pd

import rag_core as rc


def load_eval(path):
    df = pd.read_csv(path, dtype=str).fillna("")
    if df["question"].str.contains("TODO").any():
        raise SystemExit("eval/eval_set.csv masih berisi TODO. Isi dengan pertanyaan kamu sendiri dulu.")
    df["gold"] = df["gold_pasal"].apply(lambda s: {x.strip().upper() for x in s.split(";") if x.strip()})
    df["answerable"] = df["answerable"].str.strip().str.lower().eq("yes")
    return df


def first_hit_rank(hits, gold):
    for i, h in enumerate(hits, 1):
        if (h["pasal"] or "").upper() in gold:
            return i
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval-file", default="eval/eval_set.csv")
    ap.add_argument("--chunk-sizes", type=int, nargs="+", default=[500, 1000, 1500])
    ap.add_argument("--ks", type=int, nargs="+", default=[1, 3, 5])
    ap.add_argument("--with-llm", action="store_true", help="Hasilkan jawaban LLM untuk konfigurasi terbaik")
    args = ap.parse_args()

    pdfs = sorted(str(p) for p in Path("data").glob("*.pdf"))
    if not pdfs:
        raise SystemExit("Taruh PDF di folder data/ dulu.")
    df = load_eval(args.eval_file)
    answerable = df[df["answerable"]]
    kmax = max(args.ks)

    rows = []
    for cs in args.chunk_sizes:
        coll = f"eval_cs{cs}"
        n_chunks = rc.build_index(pdfs, coll, cs, overlap=int(cs * 0.15))
        ranks = [first_hit_rank(rc.retrieve(q, coll, kmax), g) for q, g in zip(answerable["question"], answerable["gold"])]
        for k in args.ks:
            hit = [r is not None and r <= k for r in ranks]
            rr = [1 / r if (r is not None and r <= k) else 0 for r in ranks]
            rows.append(
                {
                    "chunk_size": cs,
                    "n_chunks": n_chunks,
                    "k": k,
                    "hit_rate": round(sum(hit) / len(hit), 3),
                    "mrr": round(sum(rr) / len(rr), 3),
                    "n_questions": len(ranks),
                }
            )

    res = pd.DataFrame(rows)
    Path("results").mkdir(exist_ok=True)
    res.to_csv("results/retrieval_results.csv", index=False)
    print("\nHASIL RETRIEVAL\n" + res.to_string(index=False))

    if args.with_llm:
        best = res.sort_values(["hit_rate", "mrr"], ascending=False).iloc[0]
        coll, k = f"eval_cs{int(best['chunk_size'])}", int(best["k"])
        print(f"\nMenghasilkan jawaban LLM dengan konfigurasi terbaik: chunk_size={best['chunk_size']}, k={k}")
        out_rows = []
        for _, r in df.iterrows():
            out = rc.answer(r["question"], coll, k)
            out_rows.append(
                {
                    "question": r["question"],
                    "answerable": r["answerable"],
                    "gold_pasal": r["gold_pasal"],
                    "retrieved_pasal": ";".join(str(h["pasal"]) for h in out["sources"]),
                    "answer": out["answer"],
                    "abstained": rc.NOT_FOUND in out["answer"],
                    "manual_grade": "",  # isi sendiri: benar / sebagian / salah
                }
            )
        ans = pd.DataFrame(out_rows)
        ans.to_csv("results/answers_for_grading.csv", index=False)
        un = ans[~ans["answerable"]]
        an = ans[ans["answerable"]]
        if len(un):
            print(f"Abstain benar pada pertanyaan tak terjawab: {un['abstained'].mean():.2f}")
        if len(an):
            print(f"Abstain salah pada pertanyaan terjawab: {an['abstained'].mean():.2f}")
        print("Nilai kolom manual_grade di results/answers_for_grading.csv secara manual.")


if __name__ == "__main__":
    main()
