import re

def _split_long_paragraph(paragraph: str, max_chars: int) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", paragraph)
    chunks = []
    current = ""
    for sent in sentences:
        if len(current) + len(sent) + 1 > max_chars and current:
            chunks.append(current.strip())
            current = sent
        else:
            current = f"{current} {sent}".strip() if current else sent
    if current:
        chunks.append(current.strip())
    return chunks

def chunk_text(text: str, max_chars: int = 1000, overlap_chars: int = 200) -> list[str]:
    if not text:
        return []

    paragraphs = re.split(r"\n\s*\n", text.strip())
    chunks = []
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current) + len(para) + 1 > max_chars and current:
            chunks.append(current.strip())
            overlap = current[-overlap_chars:] if len(current) > overlap_chars else current
            current = f"{overlap}\n{para}".strip()
        elif len(para) > max_chars:
            if current:
                chunks.append(current.strip())
            chunks.extend(_split_long_paragraph(para, max_chars))
            current = ""
        else:
            current = f"{current}\n{para}".strip() if current else para

    if current:
        chunks.append(current.strip())

    return chunks

# For retrieval formatting
def format_chunks_as_context(chunks: list[dict]) -> str:
    if not chunks:
        return ""

    parts = []
    for i, c in enumerate(chunks, 1):
        source = f"[{c['document_type']}]" if "patient_id" not in c else f"[{c['document_type']} — paciente {c['patient_id']}]"
        parts.append(f"--- Documento {i} {source} (relevancia: {c['score']:.2f}) ---\n{c['chunk_text']}")

    return "\n\n" + "\n\n".join(parts)