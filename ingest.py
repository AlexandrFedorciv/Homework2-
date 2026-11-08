"""PDF -> text -> chunks -> embeddings -> Chroma. Usage: python ingest.py [pdf_folder]"""
import sys
from pathlib import Path

import chromadb
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).parent
DB_PATH = ROOT / "chroma_db"
COLLECTION = "pdfs"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
# all-MiniLM-L6-v2 truncates at 256 tokens, roughly 1000 characters of English.
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150


def chunk_text(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Split text into overlapping chunks, breaking on word boundaries."""
    text = " ".join(text.split())
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            space = text.rfind(" ", start + overlap + 1, end)
            if space != -1:
                end = space
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = text.find(" ", end - overlap, end) + 1 or end - overlap
    return chunks


def read_chunks(folder):
    """Return (ids, texts, metadatas). Page numbers are the PDF's physical pages, starting at 1."""
    ids, texts, metadatas = [], [], []
    for path in sorted(folder.glob("*.pdf")):
        try:
            pages = [page.extract_text() or "" for page in PdfReader(path).pages]
        except Exception as e:  # one broken PDF must not stop the others
            print(f"  skipped {path.name}: {e}")
            continue
        before = len(ids)
        # shortcut: chunks never cross a page, so a sentence split over two pages is cut; fine for exact page citations.
        for number, page_text in enumerate(pages, start=1):
            for i, chunk in enumerate(chunk_text(page_text)):
                ids.append(f"{path.name}:{number}:{i}")
                texts.append(chunk)
                metadatas.append({"filename": path.name, "page": number})
        count = len(ids) - before
        print(f"  {path.name}: {len(pages)} pages, {count} chunks" + ("  (no text, scanned PDF?)" if not count else ""))
    return ids, texts, metadatas


def main():
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "pdfs"
    print(f"Reading {folder}")
    ids, texts, metadatas = read_chunks(folder)
    if not ids:
        sys.exit(f"No extractable text found in PDFs under {folder}")

    print(f"Embedding {len(ids)} chunks with {EMBED_MODEL}")
    embeddings = SentenceTransformer(EMBED_MODEL).encode(texts, normalize_embeddings=True, show_progress_bar=True).tolist()

    # Replace the index only now, so a failed run above leaves the old one intact.
    client = chromadb.PersistentClient(path=str(DB_PATH))
    if COLLECTION in [c.name for c in client.list_collections()]:
        client.delete_collection(COLLECTION)
    collection = client.create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})
    batch = client.get_max_batch_size()
    for i in range(0, len(ids), batch):
        collection.add(ids=ids[i:i + batch], documents=texts[i:i + batch], metadatas=metadatas[i:i + batch], embeddings=embeddings[i:i + batch])
    print(f"Stored {collection.count()} chunks in {DB_PATH}")


if __name__ == "__main__":
    main()
