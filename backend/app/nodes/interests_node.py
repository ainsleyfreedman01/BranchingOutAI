# backend/app/langgraph_agent/nodes/interests_node.py
from app.config import client
from app.state_manager import save_state, get_state
from app.utils.keywords import extract_keywords
import re
try:
    import spacy
    _SPACY_AVAILABLE = True
except Exception:
    spacy = None
    _SPACY_AVAILABLE = False

class InterestsNode:
    def process(self, user_input, state, session_id=None):
        """Process user interests to suggest industries.

        Args:
            self: InterestsNode instance.
            user_input (str): The user's stated interests.
            state (dict): The current session state.
            session_id (str, optional): The user's session ID for state saving.
        """
        # If session_id provided, prefer latest saved state from Supabase, but always recompute interests from current input
        if session_id:
            saved = get_state(session_id)
            if isinstance(saved, dict):
                merged = dict(saved)
                merged.update(state or {})
                state = merged

        # Prefer AI parsing first to extract interests as a JSON list
        canonical_interests = []
        try:
            ai_resp = client.chat(
                messages=[
                    {"role": "system", "content": "You identify the user's interests."},
                    {"role": "user", "content": (
                        "What are the user's interests based on this input? "
                        "Return ONLY a JSON array of interest phrases. Input: " + user_input
                    )}
                ]
            )
            import json
            parsed = None
            try:
                parsed = json.loads(ai_resp)
            except Exception:
                m = re.search(r"\[(.*?)\]", ai_resp, re.S)
                if m:
                    try:
                        parsed = json.loads("[" + m.group(1) + "]")
                    except Exception:
                        parsed = None
            if isinstance(parsed, list):
                canonical_interests = [str(x).strip() for x in parsed if str(x).strip()]
        except Exception:
            canonical_interests = []

        # Fallback: deterministic split + normalization if AI fails
        if not canonical_interests:
            raw_items = [s.strip() for s in re.split(r"\band\b|,|/|;", user_input, flags=re.IGNORECASE) if s.strip()]
            all_low = user_input.lower()
            has_devops = bool(re.search(r"\bdev\s*ops\b|\bdevops\b", all_low))
            has_mlops = bool(re.search(r"\bmlops\b|machine\s*learning\s*ops|\bml\s*ops\b", all_low))
            for item in raw_items:
                low = item.lower().strip()
                if re.search(r"\bux\s*/\s*ui\b|\bux\b.*\bui\b", low):
                    canonical_interests.append("UX/UI")
                elif re.search(r"\bdev\s*ops\b|\bdevops\b", low) or re.search(r"\bmlops\b|machine\s*learning\s*ops|\bml\s*ops\b", low):
                    # skip here; we'll append canonical tokens below
                    pass
                else:
                    canonical_interests.append(item.title())
            if has_devops:
                canonical_interests.append("DevOps")
            if has_mlops:
                canonical_interests.append("MLOps")

        # Helper: split obviously combined phrases into distinct interests
        def _split_combined_phrase(p: str):
            p = p.strip()
            if not p:
                return []
            # Treat MLOps variations as a single token to avoid splitting
            normalized = re.sub(r"machine\s*learning\s*ops", "mlops", p, flags=re.I)
            normalized = re.sub(r"ml\s*ops", "mlops", normalized, flags=re.I)
            normalized = re.sub(r"dev\s*ops", "devops", normalized, flags=re.I)
            # Prefer spaCy noun chunks to separate multiple phrases within one item
            if _SPACY_AVAILABLE:
                try:
                    try:
                        nlp = spacy.load("en_core_web_sm")
                    except Exception:
                        nlp = spacy.load("en")
                    doc = nlp(normalized)
                    phrases = []
                    for chunk in doc.noun_chunks:
                        c = chunk.text.strip()
                        if c:
                            phrases.append(c)
                    if phrases:
                        return [w.title() for w in phrases]
                except Exception:
                    pass
            # Fallback: split on common separators
            parts = [s.strip() for s in re.split(r"\band\b|,|/|;", normalized, flags=re.IGNORECASE) if s.strip()]
            # If tokens include mlops/devops, return canonical entries
            if any(re.search(r"\bmlops\b", s, re.I) for s in parts):
                return ["MLOps"]
            if any(re.search(r"\bdevops\b", s, re.I) for s in parts):
                return ["DevOps"]
            # Otherwise, just return the split parts in title case without bigram segmentation
            return [s.title() for s in parts] if parts else []

        # Deduplicate (preserve order)
        seen = set()
        final_interests = []
        # Helper to fix acronym capitalization inside phrases
        def _fix_acronyms(text: str) -> str:
            if not text:
                return text
            # Replace common acronyms with correct casing
            acronyms = {
                'ux': 'UX',
                'ui': 'UI',
                'ai': 'AI',
                'ml': 'ML',
                'nlp': 'NLP'
            }
            def repl(m):
                w = m.group(0)
                lw = w.lower()
                return acronyms.get(lw, w)
            # Apply on word boundaries
            return re.sub(r"\b(ux|ui|ai|ml|nlp)\b", repl, text, flags=re.I)

        for v in canonical_interests:
            v = str(v).strip()
            # Normalize common variants early
            v_norm = v
            if re.search(r"\bux\b.*\bui\b|ux\s*/\s*ui", v, re.I):
                v_norm = "UX/UI"
            elif re.search(r"\bdev\s*ops\b|\bdevops\b", v, re.I):
                v_norm = "DevOps"
            elif re.search(r"\bmlops\b|machine\s*learning\s*ops|\bml\s*ops\b", v, re.I):
                v_norm = "MLOps"
            else:
                v_norm = _fix_acronyms(v.title())
            key = v_norm.lower()
            if key in seen:
                continue
            seen.add(key)
            final_interests.append(v_norm)

        # Normalize common abbreviations and phrasing for recognizability
        def _normalize_interest(s: str) -> str:
            raw = s.strip()
            if not raw:
                return s
            words = re.findall(r"[A-Za-z]+", raw.lower())
            ws = set(words)
            # UX/UI variants
            if 'ux' in ws and 'ui' in ws:
                return 'UX/UI'
            # DevOps
            if 'devops' in ws or ('dev' in ws and 'ops' in ws):
                return 'DevOps'
            # MLOps variants
            if 'mlops' in ws or (('ml' in ws or 'machine' in ws) and 'ops' in ws):
                return 'MLOps'
            # Front End Development
            joined = " ".join(words)
            if (
                ('front' in ws and 'end' in ws and ('dev' in ws or 'development' in ws)) or
                re.search(r"front\s*-?\s*end\s*(dev|development)", joined) or
                re.search(r"frontend\s*(dev|development)", joined) or
                joined.strip() in ("end dev", "end development", "front dev")
            ):
                return 'Front End Development'
            # Backend Microservices
            if 'backend' in ws and 'microservices' in ws:
                return 'Backend Microservices'
            # Generic dev -> Development replacement
            if 'dev' in ws and len(words) == 2:
                # e.g., 'end dev' -> 'End Development', but prefer 'Front End Development' rule above
                return f"{words[0].title()} Development"
            return raw.title()

        final_interests = [_normalize_interest(x) for x in final_interests]
        # Final direct replacements for stubborn cases
        direct_map = {
            "End Dev": "Front End Development",
            "End Development": "Front End Development",
            "Front Dev": "Front End Development",
        }
        final_interests = [direct_map.get(i, i) for i in final_interests]

        # Consolidate DevOps/MLOps patterns produced by bigram splits
        # e.g., ["Devops Ml", "Ops"] -> ["DevOps", "MLOps"]
        consolidated = []
        seen_lower = set()
        for i in final_interests:
            low = i.lower().strip()
            if low not in seen_lower:
                seen_lower.add(low)
                consolidated.append(i)

        # Pass 1: canonicalize direct tokens
        for idx, val in enumerate(consolidated):
            if re.search(r"\bdev\s*ops\b|\bdevops\b", val, re.I):
                consolidated[idx] = "DevOps"
            if re.search(r"\bmlops\b|machine\s*learning\s*ops", val, re.I):
                consolidated[idx] = "MLOps"

        # Pass 2: detect mixed fragments like "Devops Ml" and split into DevOps + MLOps
        rebuilt = []
        for v in consolidated:
            has_devops = bool(re.search(r"\bdev\s*ops\b|\bdevops\b", v, re.I))
            has_ml = bool(re.search(r"\bml\b|\bmlops\b|machine\s*learning", v, re.I))
            has_ops = bool(re.search(r"\bops\b", v, re.I))
            if has_devops and has_ml:
                if "DevOps" not in rebuilt:
                    rebuilt.append("DevOps")
                if "MLOps" not in rebuilt:
                    rebuilt.append("MLOps")
            else:
                rebuilt.append(v)

        # Pass 3: if we have separate ML and OPS fragments anywhere, add MLOps and remove stray OPS
        contains_ml_fragment = any(re.search(r"^ml$|mlops|machine\s*learning", i, re.I) for i in rebuilt)
        contains_ops_fragment = any(re.fullmatch(r"ops", i, re.I) for i in rebuilt)
        if contains_ml_fragment and contains_ops_fragment:
            rebuilt = [v for v in rebuilt if not re.fullmatch(r"ops", v, re.I)]
            if "MLOps" not in rebuilt:
                rebuilt.append("MLOps")

        # Final pass: title/case fixes
        final_interests = []
        for v in rebuilt:
            if v.lower() in ("devops",):
                final_interests.append("DevOps")
            elif v.lower() in ("mlops",):
                final_interests.append("MLOps")
            else:
                final_interests.append(v)

        # Extra normalization: canonicalize UX/UI variants into a single token
        normalized_final = []
        seen_norm = set()
        # helper to normalize individual token into canonical form if it matches UX/UI
        def _is_ui_variant(s: str) -> bool:
            s_low = s.lower()
            # direct patterns that indicate UX/UI intent
            patterns = [r"\bux\b", r"\bui\b", r"ux/ui", r"ui/ux", r"user experience", r"user interface", r"ui design", r"ux design"]
            for p in patterns:
                if re.search(p, s_low):
                    return True
            return False

        has_ui_variant = any(_is_ui_variant(x) for x in final_interests)
        for v in final_interests:
            if _is_ui_variant(v):
                # ensure a single canonical UX/UI token
                if "ux/ui" not in seen_norm:
                    normalized_final.append("UX/UI")
                    seen_norm.add("ux/ui")
                continue
            key = v.lower().strip()
            if key in seen_norm:
                continue
            seen_norm.add(key)
            normalized_final.append(v)

        final_interests = normalized_final

        # Join adjacent single-word tokens into multi-word interests when
        # the original `user_input` contains that phrase AND the phrase is
        # one of a small whitelist of common multi-word interests. This
        # avoids aggressive joining like 'Sustainability Marketing'.
        MULTI_WORD_WHITELIST = {
            "museum curation",
            "jigsaw puzzles",
            "art history",
            "product management",
            "data analysis",
            "user research",
            "user experience",
            "user interface",
            "front end",
            "machine learning",
            "graphic design",
            "community development",
            "public policy",
            "arts and crafts",
        }

        joined = []
        i = 0
        while i < len(final_interests):
            cur = final_interests[i]
            if i + 1 < len(final_interests):
                nxt = final_interests[i + 1]
                if re.fullmatch(r"[A-Za-z]+", cur) and re.fullmatch(r"[A-Za-z]+", nxt):
                    joined_lower = f"{cur.lower()} {nxt.lower()}"
                    pattern = re.compile(r"\b" + re.escape(cur) + r"\s+" + re.escape(nxt) + r"\b", re.I)
                    if joined_lower in MULTI_WORD_WHITELIST and pattern.search(user_input):
                        joined.append(f"{cur} {nxt}".title())
                        i += 2
                        continue
            joined.append(cur)
            i += 1

        final_interests = joined

        # Specific fix: replace any lingering 'Devops Ml' and remove stray 'Ops'
        cleaned = []
        add_mlops = False
        for v in final_interests:
            if re.search(r"^devops\s+ml$", v, re.I):
                if "DevOps" not in cleaned:
                    cleaned.append("DevOps")
                add_mlops = True
                continue
            if re.fullmatch(r"ops", v, re.I):
                add_mlops = True
                continue
            cleaned.append(v)
        if add_mlops and "MLOps" not in cleaned:
            cleaned.append("MLOps")
        final_interests = cleaned
        # If AI returned nothing, keep fallback interests (already processed above)

        # Always replace interests with the canonical ones extracted from current input
        state["interests"] = final_interests if final_interests else ([user_input] if user_input else [])

        # Ask OpenAI for 2-3 industries (JSON list only). This call may fail
        # in environments without OPENAI_API_KEY or network access; in that
        # case we fall back to a deterministic heuristic.
        industries_list = None
        try:
            response = client.chat(
                messages=[
                    {"role": "system", "content": "You are a career exploration AI."},
                    {"role": "user", "content": f"The user is interested in: {', '.join(final_interests) if final_interests else user_input}. Suggest 2-3 broad industries. Return ONLY a JSON array (no code fences)."}
                ]
            )

            # If the client returned a list-like object already, use it
            if isinstance(response, (list, tuple)):
                industries_list = [str(x).strip() for x in response if str(x).strip()]
            else:
                # Robustly normalize response to a Python list
                resp_text = str(response).strip()
                # Strip common code fences if present
                resp_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", resp_text, flags=re.I|re.M)
                try:
                    import json
                    parsed = json.loads(resp_text)
                    if isinstance(parsed, list):
                        industries_list = [str(x).strip() for x in parsed if str(x).strip()]
                except Exception:
                    # Attempt to extract a bracketed JSON array from the text
                    m = re.search(r"\[(.*?)\]", resp_text, re.S)
                    if m:
                        try:
                            candidate = "[" + m.group(1) + "]"
                            try:
                                parsed = json.loads(candidate)
                            except Exception:
                                # Handle Python-style repr lists using single quotes
                                try:
                                    parsed = json.loads(candidate.replace("'", '"'))
                                except Exception:
                                    parsed = None
                            if isinstance(parsed, list):
                                industries_list = [str(x).strip() for x in parsed if str(x).strip()]
                        except Exception:
                            industries_list = None
                if industries_list is None:
                    # Fallback: best-effort plain text split of the response
                    parts = [s.strip() for s in re.split(r",|/|;|\n", resp_text) if s.strip()]
                    industries_list = parts[:3]
        except Exception:
            # If the LLM call fails (no API key, network issues), fall back
            # to a deterministic heuristic based on extracted interests or
            # the original user input.
            src = final_interests if final_interests else [user_input]
            combined = ", ".join(src)
            parts = [s.strip() for s in re.split(r",|/|;|\n", combined) if s.strip()]
            # Pick a few broad terms from the interests as best-effort industries
            industries_list = [p.title() for p in parts][:3]
        state["industries"] = industries_list

        # Save to Supabase
        if session_id:
            save_state(session_id, state)

        return "Here are some industries you might explore.", state