"""Simple keyword extraction utility.

This is intentionally lightweight and deterministic: it tokenizes the input,
removes common English stopwords and punctuation, and returns the first
`max_keywords` remaining tokens. It avoids heavy NLP dependencies so tests run quickly.
"""

from typing import List
import re

# Try to use spaCy when available for better extraction; fall back to the simple
# extractor if spaCy isn't installed or the model isn't available.
try:  # pragma: no cover - environment dependent
    import spacy
    _SPACY_AVAILABLE = True
except Exception:
    spacy = None
    _SPACY_AVAILABLE = False

# A small stopword list tuned for short user inputs. Used by fallback extractor.
_STOPWORDS = {
    "i", "me", "my", "we", "our", "you", "your", "he", "she", "they",
    "them", "it", "is", "are", "am", "was", "were", "be", "been",
    "the", "a", "an", "and", "or", "but", "if", "then", "so", "to",
    "of", "in", "on", "for", "with", "about", "as", "at", "by",
    "from", "that", "this", "these", "those", "like"
}


def _simple_extract(text: str, max_keywords: int = 3) -> List[str]:
    """Deterministic fallback extractor used when spaCy is unavailable."""
    if not text:
        return []
    cleaned = re.sub(r"[^\w\s-]", " ", text.lower())
    tokens = [t for t in cleaned.split() if len(t) > 1 and t not in _STOPWORDS]
    seen = set()
    keywords = []
    for t in tokens:
        if t in seen:
            continue
        seen.add(t)
        keywords.append(t)
        if len(keywords) >= max_keywords:
            break
    return [k.capitalize() for k in keywords]


def extract_keywords(text: str, max_keywords: int = 3) -> List[str]:
    """Extract up to `max_keywords` meaningful tokens from `text`.

    If spaCy and a model are installed, uses spaCy to extract nouns and
    proper nouns (preserving order). Otherwise falls back to a simple
    stopword-based tokenizer.
    """
    if not text:
        return []

    if _SPACY_AVAILABLE:
        try:  # pragma: no cover - exercised when spaCy is available in env
            # Prefer the lightweight English model if present
            try:
                nlp = spacy.load("en_core_web_sm")
            except Exception:
                # Try the generic English model name fallback
                nlp = spacy.load("en")
            doc = nlp(text)
            keywords = []
            seen = set()

            def _clean_phrase(text_part: str) -> str:
                # Remove extra spaces and stopwords inside the phrase, keep order
                toks = [w for w in re.findall(r"[A-Za-z]+", text_part.lower()) if w not in _STOPWORDS]
                if not toks:
                    return ""
                return " ".join(toks).title()

            # Global greedy non-overlapping noun bigrams to strongly prefer phrases
            noun_seq = [t for t in doc if t.pos_ in ("NOUN", "PROPN")]
            i = 0
            while i < len(noun_seq) - 1 and len(keywords) < max_keywords:
                a = noun_seq[i].text
                b = noun_seq[i+1].text
                pair_clean = _clean_phrase(f"{a} {b}")
                if pair_clean:
                    pl = pair_clean.lower()
                    if pl not in seen:
                        seen.add(pl)
                        keywords.append(pair_clean)
                i += 2

            # First prefer noun chunks (split on 'and' to separate distinct phrases) if we still need more
            phrase_pool = []
            for chunk in doc.noun_chunks:
                raw = chunk.text.strip()
                if not raw:
                    continue
                # Split on 'and' (coordinating conjunction) to avoid combining distinct phrases
                parts = [p.strip() for p in re.split(r"\band\b", raw, flags=re.IGNORECASE) if p.strip()]
                for part in parts:
                    # When grammar is poor, chunks can swallow several noun phrases.
                    # Use token POS within this part to split consecutive NOUN/PROPN pairs.
                    subdoc = nlp(part)
                    noun_tokens = [t for t in subdoc if t.pos_ in ("NOUN", "PROPN")]
                    # Build non-overlapping bigrams of adjacent nouns (greedy)
                    i = 0
                    while i < len(noun_tokens) - 1 and len(phrase_pool) < max_keywords:
                        a = noun_tokens[i].text
                        b = noun_tokens[i+1].text
                        pair_clean = _clean_phrase(f"{a} {b}")
                        if pair_clean:
                            pl = pair_clean.lower()
                            if pl not in seen:
                                seen.add(pl)
                                phrase_pool.append(pair_clean)
                        i += 2  # advance by two to avoid overlapping pairs
                    if len(phrase_pool) < max_keywords:
                        # If we still need more, add remaining single nouns not already covered
                        for t in noun_tokens:
                            if len(phrase_pool) >= max_keywords:
                                break
                            single = _clean_phrase(t.text)
                            sl = single.lower()
                            if not single or sl in seen:
                                continue
                            # Skip if part of any selected bigram
                            if any(sl in p.lower().split() for p in phrase_pool):
                                continue
                            seen.add(sl)
                            phrase_pool.append(single)
                    if len(phrase_pool) >= max_keywords:
                        break
                if len(phrase_pool) >= max_keywords:
                    break

            # If poor grammar caused chunks to merge and we still need more, chunk-based phrases will fill

            # Add chunk-derived phrases to keywords respecting max limit
            if len(keywords) < max_keywords and phrase_pool:
                # If any phrase is longer than two words, split into non-overlapping noun bigrams
                expanded = []
                for p in phrase_pool:
                    words = [w for w in re.findall(r"[A-Za-z]+", p.lower()) if w not in _STOPWORDS]
                    if len(words) > 2:
                        for j in range(0, len(words) - 1, 2):
                            expanded.append(" ".join(words[j:j+2]).title())
                    else:
                        expanded.append(p)
                for p in expanded:
                    if len(keywords) >= max_keywords:
                        break
                    pl = p.lower()
                    if pl in seen:
                        continue
                    seen.add(pl)
                    keywords.append(p)

            # If not enough, fall back to individual noun tokens preserving order
            if len(keywords) < max_keywords:
                for token in doc:
                    if token.pos_ in ("NOUN", "PROPN") and len(token.text) > 1:
                        t = token.text.strip()
                        tl = t.lower()
                        if tl in _STOPWORDS:
                            continue
                        # Skip singles that are already part of selected phrases
                        if tl in seen or any(tl in k.lower().split() for k in keywords):
                            continue
                        seen.add(tl)
                        keywords.append(t.title())
                        if len(keywords) >= max_keywords:
                            break

            if keywords:
                return keywords
        except Exception:
            # If spaCy fails for any reason, fall back to simple extractor
            pass

    # Fallback: build bigrams first (to capture phrases like 'product design'), then singles
    if not text:
        return []
    cleaned = re.sub(r"[^\w\s-]", " ", text.lower())
    tokens = [t for t in cleaned.split() if len(t) > 1 and t not in _STOPWORDS]

    # Build bigrams from adjacent non-stopword tokens, prefer bigrams when present
    bigrams = []
    for a, b in zip(tokens, tokens[1:]):
        if a not in _STOPWORDS and b not in _STOPWORDS:
            bigrams.append(f"{a} {b}")

    # Candidates: bigrams first (preserve order), then singles not contained within chosen bigrams
    candidates = []
    seen = set()
    for bi in bigrams:
        bl = bi.lower()
        if bl in seen:
            continue
        seen.add(bl)
        candidates.append(bi)
        if len(candidates) >= max_keywords:
            break

    if len(candidates) < max_keywords:
        for t in tokens:
            # Skip if token is already part of any selected bigram
            if any(t in bi.split() for bi in candidates):
                continue
            tl = t.lower()
            if tl in seen:
                continue
            seen.add(tl)
            candidates.append(t)
            if len(candidates) >= max_keywords:
                break

    return [c.title() for c in candidates]
