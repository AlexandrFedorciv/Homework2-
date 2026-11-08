"""Run with: python test_rag.py"""
from ask import IDK, UNVERIFIED, check_citations
from ingest import chunk_text

HITS = [{"filename": "a.pdf", "page": 3, "text": "x", "distance": 0.1}]

# Chunks respect the size limit, overlap, keep every word and terminate.
words = " ".join(f"word{i}" for i in range(1000))
chunks = chunk_text(words, size=100, overlap=20)
assert all(len(c) <= 100 for c in chunks)
assert all(a.split()[-1] in b.split() for a, b in zip(chunks, chunks[1:]))
assert {w for c in chunks for w in c.split()} == set(words.split())
assert chunk_text("   ") == []
assert chunk_text("short") == ["short"]
assert chunk_text("x" * 250, size=100, overlap=20)[0] == "x" * 100  # no spaces at all

# Real citations survive, invented ones are flagged, and no real citation means no answer.
assert check_citations("Yes [a.pdf, p. 3].", HITS) == "Yes [a.pdf, p. 3]."
assert check_citations("Yes [a.pdf, p. 3]. No [a.pdf, p. 9].", HITS) == f"Yes [a.pdf, p. 3]. No {UNVERIFIED}."
assert check_citations("Yes [b.pdf, p. 3].", HITS) == IDK
assert check_citations("Confident claim with no citation.", HITS) == IDK
assert check_citations(IDK, HITS) == IDK

# Look-alike characters from real model output count as the required form.
assert check_citations("Yes【a.pdf, p. 3】", HITS) == "Yes[a.pdf, p. 3]"
assert check_citations("Yes [1, p. 3]", HITS) == IDK  # a source number is not a filename
assert check_citations("Yes [​a.pdf, p. 3]", HITS) == "Yes [a.pdf, p. 3]"
assert check_citations("Yes [ a.pdf, p. 3 ]", HITS) == "Yes [a.pdf, p. 3]"
assert check_citations("Yes [ a . p d f , p. 3]", HITS) == "Yes [a.pdf, p. 3]"
assert check_citations("Yes [ A .PDF, p. 3]", HITS) == "Yes [a.pdf, p. 3]"

print("ok")
