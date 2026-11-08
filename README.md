# Ask-Your-PDFs

A Python RAG command-line app. It ingests a folder of PDFs and answers questions with page-level citations in the form `[filename, p. N]`. If the documents don't contain the answer, it says `I don't know based on the provided documents.`

```
PDF -> text per page -> overlapping chunks -> embeddings -> Chroma
question -> embedding -> top-k search -> relevance cutoff -> LLM -> citation check -> answer
```

| Part | Choice |
|---|---|
| PDF text | `pypdf`, one page at a time, so every chunk keeps its exact page |
| Chunks | 800 characters with 150 overlap, split on word boundaries; metadata is `filename` and `page` |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2`, local and free (about 90 MB, downloaded on first run) |
| Vector store | Chroma, persistent, cosine distance, stored in `chroma_db/` |
| Retrieval | top-k semantic search, default `k = 5` |
| LLM | Anthropic by default, any OpenAI-compatible API, or an offline `mock` |

## Setup

Needs Python 3.10 to 3.13 (tested on 3.13).

```powershell
git clone <this-repo-url>
cd <this-repo>
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env          # macOS/Linux: cp .env.example .env
```

Then edit `.env` and pick one provider:

| Provider | `.env` |
|---|---|
| Anthropic | `LLM_PROVIDER=anthropic` and `ANTHROPIC_API_KEY=...` |
| Groq (free tier) | `LLM_PROVIDER=openai`, `OPENAI_API_KEY=...`, `OPENAI_BASE_URL=https://api.groq.com/openai/v1`, `LLM_MODEL=openai/gpt-oss-120b` |
| Ollama (local, no key) | `LLM_PROVIDER=openai`, `OPENAI_BASE_URL=http://localhost:11434/v1`, `LLM_MODEL=qwen3:8b` |
| Mock (offline, no key) | `LLM_PROVIDER=mock`, which quotes the best chunk so retrieval and citations can be tried without an LLM |

With Anthropic, the default model is `claude-opus-5-5`. Set `LLM_MODEL` to use another one.

## Usage

```powershell
python ingest.py                  # index ./pdfs, or: python ingest.py path\to\folder
python ask.py "What are the four functions of the AI RMF Core?"
python ask.py --k 8 "Should verifiers require periodic password changes?"
python ask.py                     # interactive prompt, empty line to quit
python test_rag.py                # self-check for chunking and citation logic
```

Running `ingest.py` again rebuilds the index from scratch.

## Examples

### With an LLM

These show the expected format. The facts and citations were checked against the PDFs, but they are not captured model output, and a model's wording will vary.

```text
> python ask.py "What are the six functions of the NIST Cybersecurity Framework 2.0?"
The six CSF Core functions are Govern, Identify, Protect, Detect, Respond and Recover [nist-csf-2.0.pdf, p. 10].

> python ask.py "Should verifiers require periodic password changes?"
No. Verifiers should not require memorized secrets to be changed arbitrarily, such as periodically, but they must force a change if there is evidence the authenticator was compromised [nist-sp-800-63b.pdf, p. 25].

> python ask.py "What is a Key Decision Point?"
A Key Decision Point is the event at which the decision authority determines whether a program or project is ready to progress to the next phase of the life cycle, or to the next KDP [nasa-systems-engineering-handbook.pdf, p. 231].

> python ask.py "What is the salary of a NASA astronaut?"
I don't know based on the provided documents.
```

### Offline mock (actual output)

With `LLM_PROVIDER=mock` the app quotes the start of the best-matching chunk instead of generating an answer. The output below is unedited.

```text
> python ask.py "What is a Key Decision Point?"
(mock, no LLM) NASA Systems Engineering Handbook Rev 2 218 Term Definition/Context Iterative Application of a process to the same product or set of products to correct a discovered discrepancy or other variation from requirements. (See “recursive” and “repeatable.”) Key Decision Point The event at which the decisi... [nasa-systems-engineering-handbook.pdf, p. 231]

> python ask.py "What are the six functions of the NIST Cybersecurity Framework 2.0?"
(mock, no LLM) NIST CSWP 29 The NIST Cybersecurity Framework (CSF) 2.0 February 26, 2024 5 Fig. 2. CSF Functions The Functions should be addressed concurrently. Actions that support GOVERN, IDENTIFY, PROTECT, and DETECT should all happen continuously, and actions that support RESPOND and RECOVER should be ready at... [nist-csf-2.0.pdf, p. 10]

> python ask.py "What is the best recipe for chocolate chip cookies?"
I don't know based on the provided documents.
```

## Sample PDFs

All four are US Government publications, in the public domain, and are in `pdfs/`.

| File | Document | Pages | Chunks |
|---|---|---|---|
| `nist-ai-rmf-1.0.pdf` | [NIST AI 100-1, AI Risk Management Framework 1.0](https://nvlpubs.nist.gov/nistpubs/ai/nist.ai.100-1.pdf) | 48 | 177 |
| `nist-csf-2.0.pdf` | [NIST CSWP 29, Cybersecurity Framework 2.0](https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf) | 32 | 112 |
| `nist-sp-800-63b.pdf` | [NIST SP 800-63B, Digital Identity Guidelines](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-63b.pdf) | 80 | 329 |
| `nasa-systems-engineering-handbook.pdf` | [NASA Systems Engineering Handbook, Rev 2](https://ntrs.nasa.gov/api/citations/20170001761/downloads/20170001761.pdf) | 356 | 1328 |

## Sample questions and expected citations

Each page below was retrieved in the top 5 and was checked by hand to contain the answer. An LLM's wording will vary, and it may cite additional retrieved pages.

| Question | Expected answer | Expected citation |
|---|---|---|
| What are the four functions of the AI RMF Core? | Govern, Map, Measure, Manage | `[nist-ai-rmf-1.0.pdf, p. 25]` |
| What are the characteristics of trustworthy AI systems? | Valid and reliable; safe; secure and resilient; accountable and transparent; explainable and interpretable; privacy-enhanced; fair with harmful bias managed | `[nist-ai-rmf-1.0.pdf, p. 17]` |
| What are the six functions of the NIST Cybersecurity Framework 2.0? | Govern, Identify, Protect, Detect, Respond, Recover | `[nist-csf-2.0.pdf, p. 10]` |
| What are the four Cybersecurity Framework Tiers? | Partial, Risk Informed, Repeatable, Adaptive | `[nist-csf-2.0.pdf, p. 12]` or `[nist-csf-2.0.pdf, p. 31]` |
| What is the minimum length of a memorized secret chosen by a subscriber? | At least 8 characters | `[nist-sp-800-63b.pdf, p. 24]` |
| Should verifiers require periodic password changes? | No, they should not require periodic changes, but must force a change after evidence of compromise | `[nist-sp-800-63b.pdf, p. 25]` |
| Into which two major stages does NASA divide the project life cycle? | Formulation and Implementation | `[nasa-systems-engineering-handbook.pdf, p. 32]` |
| What is a Key Decision Point? | The event at which the decision authority determines a project's readiness to move to the next phase | `[nasa-systems-engineering-handbook.pdf, p. 231]` |

Questions the documents can't answer:

| Question | Expected result | Stopped by |
|---|---|---|
| What is the capital of Australia? | `I don't know based on the provided documents.` | Relevance cutoff, so the LLM is never called |
| What is the best recipe for chocolate chip cookies? | `I don't know based on the provided documents.` | Relevance cutoff, so the LLM is never called |
| What is the salary of a NASA astronaut? | `I don't know based on the provided documents.` | The LLM, because the question is near the corpus topic and passes the cutoff |

Page numbers are the PDF's physical pages (what a PDF viewer shows), not the numbers printed on the paper. For example, physical page 10 of the Cybersecurity Framework is printed as page 5.

## How "I don't know" works

1. **Relevance cutoff.** Chunks with a cosine distance above 0.6 are dropped. If none remain, the app answers `I don't know` without calling the LLM. On this corpus, 8 answerable questions had a best distance of 0.22 to 0.45, and 7 clearly off-topic questions had 0.75 to 0.86.
2. **Prompt.** The LLM may use only the supplied chunks and must reply with the exact `I don't know` sentence when they don't contain the answer. This handles near-topic questions, which measured 0.47 to 0.62 and can pass the cutoff.
3. **Citation check.** Citations are compared with the retrieved chunks. A citation to a page that wasn't retrieved is replaced with a visible `[unverified: cited page was not retrieved]`. An answer with no real citation becomes `I don't know`.

Text from PDFs is treated as untrusted: it is escaped, wrapped in `<source>` tags, and the LLM is told not to follow instructions found inside it.

## Limitations

- Scanned PDFs have no text layer and are reported during ingestion instead of being OCR'd.
- Chunks don't cross page boundaries, so a sentence split across two pages is cut in two.
- The 0.6 cutoff was measured on this corpus and this embedding model. Re-check it if you change either.
- Tables and figures are only as good as `pypdf`'s text extraction.
