import re

def split_into_sentences(text: str) -> list[str]:
    """
    Splits English and Hindi paragraphs into individual sentences.
    Splits on period (.), question mark (?), exclamation (!), or Devanagari danda (।).
    Filters out empty or short fragments (<= 8 characters).
    """
    if not text:
        return []
    raw_sentences = re.split(r'(?<=[.!?।])\s+', text)
    sentences = []
    for s in raw_sentences:
        s_clean = s.strip()
        if s_clean and len(s_clean) > 8:
            sentences.append(s_clean)
    return sentences
