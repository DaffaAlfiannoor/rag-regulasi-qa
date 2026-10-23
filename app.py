"""UI Streamlit.  Jalankan: streamlit run app.py

Jika env API_URL diisi (mis. http://localhost:8000), UI memanggil FastAPI.
Jika tidak, UI memanggil pipeline langsung.
"""
import os

import requests
import streamlit as st

st.set_page_config(page_title="Regulasi Q&A (RAG)", page_icon="⚖️")
st.title("Asisten Tanya-Jawab Regulasi")
st.caption("Jawaban hanya berdasarkan dokumen yang diindeks, lengkap dengan sumber pasal.")

k = st.sidebar.slider("Jumlah potongan konteks (k)", 1, 10, 4)
question = st.text_input("Pertanyaan", placeholder="Contoh: Apa saja hak subjek data pribadi?")

if st.button("Tanya") and question.strip():
    with st.spinner("Mencari dan menjawab..."):
        try:
            api = os.getenv("API_URL")
            if api:
                r = requests.post(f"{api}/ask", json={"question": question, "k": k}, timeout=120)
                r.raise_for_status()
                out = r.json()
            else:
                import rag_core as rc

                out = rc.answer(question, rc.DEFAULT_COLLECTION, k)
        except Exception as e:
            st.error(f"Gagal: {e}")
            st.stop()

    st.subheader("Jawaban")
    st.write(out["answer"])
    if out.get("mode") == "extractive":
        st.info("ANTHROPIC_API_KEY belum diisi, jadi yang tampil hanya potongan teks teratas.")

    st.subheader("Sumber")
    for h in out["sources"]:
        label = f"Pasal {h['pasal']}" if h.get("pasal") else h.get("source", "dokumen")
        with st.expander(f"{label}  (distance {h['distance']:.3f})"):
            st.write(h["text"])
