#!/usr/bin/env python3
"""Rebuild ALL question options from textbank using CA anchor — systematic fix."""

import re

TBANK = 'C:/Users/user/Downloads/CCSP questionbank.txt'
SRC = 'C:/Users/user/portfolio/ccsp-quiz/lib/questions.ts'
OUT = 'C:/Users/user/portfolio/ccsp-quiz/lib/questions_fixed.ts'

with open(TBANK, 'r', encoding='utf-8', errors='replace') as f:
    raw = f.read()
with open(SRC, 'r', encoding='utf-8', errors='replace') as f:
    src_content = f.read()

blocks = re.split(r'(?=Question#\d+Topic)', raw)
tb_entries = []
for b in blocks[1:]:
    m_q = re.match(r'Question#\d+Topic', b)
    if not m_q:
        continue
    m_ca = re.search(r'Correct Answer: ([A-Z])', b)
    m_expl = re.search(r'Explanation:\s*Correct answer:\s*([^.]+)', b)
    if not (m_ca and m_expl):
        continue
    qmark = b.find('?')
    if qmark == -1:
        continue
    qtext = b[len(m_q.group(0)):qmark + 1].strip()
    qtext = re.sub(r'\s+', ' ', qtext)
    qtext = re.sub(r'^\d+\s+', '', qtext)
    opts_raw = b[qmark + 1:m_ca.start()].strip()
    opts_clean = re.sub(r'xmexam\.taobao\.com\s*', '', opts_raw).strip()
    words = opts_clean.split()
    n = len(words)
    ca_idx = ord(m_ca.group(1)) - ord('A')
    ca_text = m_expl.group(1).strip()
    tb_entries.append({
        'qtext': qtext,
        'words': words,
        'n': n,
        'ca_idx': ca_idx,
        'ca_text': ca_text,
    })

print(f"Textbank entries: {len(tb_entries)}")

tb_index = {}
for i, t in enumerate(tb_entries):
    key = t['qtext'][:80]
    if key not in tb_index:
        tb_index[key] = []
    tb_index[key].append(i)

src_questions = []
for m in re.finditer(
    r'\n\s+\{\s+id:\s*(\d+),.*?text:\s*"([^"]+)",.*?options:\s*\[(.*?)\],.*?answer:\s*(\d+).*?explanation:\s*"([^"]+)"',
    src_content, re.DOTALL
):
    src_questions.append({
        'id': int(m.group(1)),
        'text': m.group(2),
        'opts_str': m.group(3),
        'answer': int(m.group(4)),
        'explanation': m.group(5)
    })

print(f"Source questions: {len(src_questions)}")

def js_esc(s):
    s = s.replace('\\', '\\\\')
    s = s.replace('"', '\\"')
    s = s.replace('\n', ' ')
    s = s.replace('\r', '')
    return s

def build_entry(qid, text, opts, answer, explanation):
    opts_str = '", "'.join(js_esc(o) for o in opts)
    return (
        '  {{\n'
        '    id: {},\n'
        '    text: "{}",\n'
        '    options: ["{}"],\n'
        '    answer: {},\n'
        '    explanation: "{}",\n'
        '  }},'
    ).format(qid, js_esc(text), opts_str, answer, js_esc(explanation.lstrip(',').strip()))

def equal_part(words, n):
    q, r = divmod(n, 4)
    parts = [q] * 4
    for i in range(r):
        parts[i] += 1
    sp = [0]
    acc = 0
    for p in parts:
        acc += p
        sp.append(acc)
    return [' '.join(words[sp[i]:sp[i + 1]]) for i in range(4)]

def ca_anchor_split(words, n, ca_text, ca_idx):
    """Split words into 4 options using CA anchor. CA must START an option and that option must CONTAIN the full CA phrase."""
    if n < 4:
        return None
    ca_words_full = ca_text.lower().split()[:6]  # Up to 6 words of CA
    if not ca_words_full:
        return None
    ca_first = ca_words_full[0]

    # Find positions where CA *first word* appears, then measure actual consecutive match length
    candidates = []  # (start_pos, actual_match_len)
    for start in range(n):
        # Measure how many consecutive CA words match from this position
        match_len = 0
        for k in range(len(ca_words_full)):
            if start + k >= n:
                break
            if words[start + k].lower() == ca_words_full[k]:
                match_len += 1
            else:
                break
        if match_len >= 2:  # At least 2 consecutive words to be useful
            candidates.append((start, match_len))

    if not candidates:
        return None

    best = None
    best_bal = float('inf')
    best_s1 = -1
    for ca_start, ca_len in candidates:
        # Try all split combinations where option ca_idx STARTS at ca_start
        for s1 in range(1, n - 2):
            for s2 in range(s1 + 1, n - 1):
                for s3 in range(s2 + 1, n):
                    splits = [0, s1, s2, s3, n]
                    # Option ca_idx must START at ca_start
                    if splits[ca_idx] != ca_start:
                        continue
                    # Verify the option CONTAINS full CA phrase (at least ca_len words)
                    opt_words = words[splits[ca_idx]:splits[ca_idx + 1]]
                    if len(opt_words) < ca_len:
                        continue
                    # Check that option starts with CA phrase
                    match = True
                    for k in range(ca_len):
                        if opt_words[k].lower() != ca_words_full[k]:
                            match = False
                            break
                    if not match:
                        continue
                    lens = [splits[i + 1] - splits[i] for i in range(4)]
                    bal = max(lens) - min(lens)
                    # Prefer better balance, or larger s1 when tied (more words in earlier options)
                    if best is None or bal < best_bal or (bal == best_bal and s1 > best_s1):
                        best_bal = bal
                        best_s1 = s1
                        best = [' '.join(words[splits[i]:splits[i + 1]]) for i in range(4)]
    return best

# Single-word options that indicate fragmentation (corrupted pipe-split)
FRAGMENTS = {'are', 'they', 'their', 'must', 'may', 'the', 'it', 'can', 'will', 'not', 'that', 'this',
             'when', 'which', 'what', 'how', 'why', 'where', 'who', 'all', 'both', 'each', 'every',
             'some', 'any', 'no', 'only', 'other', 'such', 'very', 'just', 'also', 'now', 'then'}

def has_fragment(opts):
    """Check if options have single-word fragment issues."""
    for o in opts:
        words = o.strip().split()
        if len(words) == 1 and words[0].lower() in FRAGMENTS:
            return True
    return False

FIXED, SKIPPED, FAILED = 0, 0, 0
lines = [
    'export interface Question {',
    '  id: number',
    '  text: string',
    '  options: string[]',
    '  answer: number // 0-based index',
    '  explanation?: string',
    '}',
    '',
    'export const questions: Question[] = [',
]

for src in src_questions:
    qid = src['id']
    src_text = src['text']
    orig_opts = re.findall(r'"([^"]+)"', src['opts_str'])
    orig_answer = src['answer']

    key = src_text[:80]
    matches = tb_index.get(key, [])

    # Only rebuild if options have fragment issues
    needs_fix = has_fragment(orig_opts)

    if not needs_fix:
        # Keep source options - they look correct
        lines.append(build_entry(qid, src_text, orig_opts, orig_answer, src['explanation']))
        SKIPPED += 1
        continue

    if not matches:
        # No textbank match - keep original
        lines.append(build_entry(qid, src_text, orig_opts, orig_answer, src['explanation']))
        continue

    tb = tb_entries[matches[0]]
    words = tb['words']
    n = tb['n']
    tb_ca_idx = tb['ca_idx']
    tb_ca_text = tb['ca_text']

    if n >= 4:
        opts = ca_anchor_split(words, n, tb_ca_text, tb_ca_idx)
        if opts:
            explanation = tb_ca_text.lstrip(',').strip() or src['explanation'].lstrip(',').strip()
            lines.append(build_entry(qid, src_text, opts, tb_ca_idx, explanation))
            FIXED += 1
        else:
            opts = equal_part(words, n)
            explanation = tb_ca_text.lstrip(',').strip() or src['explanation'].lstrip(',').strip()
            lines.append(build_entry(qid, src_text, opts, tb_ca_idx, explanation))
            FAILED += 1
    else:
        lines.append(build_entry(qid, src_text, orig_opts, orig_answer, src['explanation']))

lines.append(']')
with open(OUT, 'w', encoding='utf-8', errors='replace') as f:
    f.write('\n'.join(lines))

print(f"Fixed: {FIXED}, Skipped (already clean): {SKIPPED}, Failed (used equal): {FAILED}")
print(f"Written: {OUT}")
