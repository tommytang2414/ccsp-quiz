#!/usr/bin/env python3
"""
Fix questions where options have severe length imbalance (fragment + merged pattern).
These were missed by rebuild_questions.py because they don't have single-word FRAGMENTS.
Uses the same CA anchor algorithm to reconstruct options from textbank.
"""

import re

TBANK = 'C:/Users/user/Downloads/CCSP questionbank.txt'
SRC = 'C:/Users/user/portfolio/ccsp-quiz/lib/questions.ts'
OUT = 'C:/Users/user/portfolio/ccsp-quiz/lib/questions.ts'
BACKUP = 'C:/Users/user/portfolio/ccsp-quiz/lib/questions_pre_imbalance_fix.ts'

with open(TBANK, 'r', encoding='utf-8', errors='replace') as f:
    raw = f.read()
with open(SRC, 'r', encoding='utf-8', errors='replace') as f:
    src_content = f.read()

# Build textbank index
blocks = re.split(r'(?=Question#\d+Topic)', raw)
tb_index = {}

for b in blocks[1:]:
    m_q = re.match(r'Question#\d+Topic', b)
    if not m_q:
        continue
    qmark = b.find('?')
    if qmark == -1:
        continue
    qtext = b[len(m_q.group(0)):qmark + 1].strip()
    qtext = re.sub(r'\s+', ' ', qtext)
    qtext = re.sub(r'^\d+\s+', '', qtext)

    m_ca = re.search(r'Correct Answer: ([A-Z])', b)
    m_expl = re.search(r'Explanation:\s*Correct answer:\s*([^.]+)', b)
    if not (m_ca and m_expl):
        continue

    opts_raw = b[qmark + 1:m_ca.start()].strip()
    opts_clean = re.sub(r'xmexam\.taobao\.com\s*', '', opts_raw).strip()
    words = opts_clean.split()
    ca_idx = ord(m_ca.group(1)) - ord('A')
    ca_text = m_expl.group(1).strip()

    # Full explanation
    full_expl = re.search(r'Explanation:\s*Correct answer:\s*(.+)', b, re.DOTALL)
    expl_text = ''
    if full_expl:
        expl_text = full_expl.group(1).strip()
        expl_text = re.sub(r'\s*\(ISC\).{0,300}?Pg\s+[\d\-]+\.?', '', expl_text, flags=re.DOTALL)
        expl_text = re.sub(r'\s*The Official \(ISC\).{0,300}?Pg\s+[\d\-]+\.?', '', expl_text, flags=re.DOTALL)
        expl_text = re.sub(r'\s*\(ISC\)2 CCSP.+', '', expl_text, flags=re.DOTALL)
        expl_text = re.sub(r'\s+', ' ', expl_text).strip()

    key = qtext[:80]
    if key not in tb_index:
        tb_index[key] = {
            'words': words,
            'n': len(words),
            'ca_idx': ca_idx,
            'ca_text': ca_text,
            'explanation': expl_text,
        }

print(f"Textbank entries: {len(tb_index)}")

# Parse source
src_questions = []
for m in re.finditer(
    r'\n\s+\{\s+id:\s*(\d+),.*?text:\s*"([^"]+)",.*?options:\s*\[(.*?)\],.*?answer:\s*(\d+).*?explanation:\s*"([^"]*)"',
    src_content, re.DOTALL
):
    src_questions.append({
        'id': int(m.group(1)),
        'text': m.group(2),
        'opts_str': m.group(3),
        'answer': int(m.group(4)),
        'explanation': m.group(5),
    })

print(f"Source questions: {len(src_questions)}")


def is_imbalanced(opts):
    lengths = [len(o) for o in opts]
    word_counts = [len(o.split()) for o in opts]
    min_len = min(lengths)
    max_len = max(lengths)
    min_words = min(word_counts)
    return max_len / max(min_len, 1) > 3 and min_words <= 2


def ca_anchor_split(words, n, ca_text, ca_idx):
    if n < 4:
        return None
    ca_words_full = ca_text.lower().split()[:6]
    if not ca_words_full:
        return None

    candidates = []
    for start in range(n):
        match_len = 0
        for k in range(len(ca_words_full)):
            if start + k >= n:
                break
            if words[start + k].lower() == ca_words_full[k]:
                match_len += 1
            else:
                break
        if match_len >= 2:
            candidates.append((start, match_len))

    if not candidates:
        return None

    best = None
    best_bal = float('inf')
    best_s1 = -1
    for ca_start, ca_len in candidates:
        for s1 in range(1, n - 2):
            for s2 in range(s1 + 1, n - 1):
                for s3 in range(s2 + 1, n):
                    splits = [0, s1, s2, s3, n]
                    if splits[ca_idx] != ca_start:
                        continue
                    opt_words = words[splits[ca_idx]:splits[ca_idx + 1]]
                    if len(opt_words) < ca_len:
                        continue
                    match = True
                    for k in range(ca_len):
                        if opt_words[k].lower() != ca_words_full[k]:
                            match = False
                            break
                    if not match:
                        continue
                    lens = [splits[i + 1] - splits[i] for i in range(4)]
                    bal = max(lens) - min(lens)
                    if best is None or bal < best_bal or (bal == best_bal and s1 > best_s1):
                        best_bal = bal
                        best_s1 = s1
                        best = [' '.join(words[splits[i]:splits[i + 1]]) for i in range(4)]
    return best


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
    ).format(qid, js_esc(text), opts_str, answer, js_esc(explanation.strip()))


FIXED = SKIPPED = FAILED = NO_MATCH = 0
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
    orig_expl = src['explanation']

    if not is_imbalanced(orig_opts):
        lines.append(build_entry(qid, src_text, orig_opts, orig_answer, orig_expl))
        SKIPPED += 1
        continue

    key = src_text[:80]
    tb = tb_index.get(key)

    if not tb:
        lines.append(build_entry(qid, src_text, orig_opts, orig_answer, orig_expl))
        NO_MATCH += 1
        continue

    words = tb['words']
    n = tb['n']
    ca_idx = tb['ca_idx']
    ca_text = tb['ca_text']
    new_expl = tb['explanation'] or orig_expl

    if n >= 4:
        opts = ca_anchor_split(words, n, ca_text, ca_idx)
        if opts:
            lines.append(build_entry(qid, src_text, opts, ca_idx, new_expl))
            FIXED += 1
        else:
            opts = equal_part(words, n)
            lines.append(build_entry(qid, src_text, opts, ca_idx, new_expl))
            FAILED += 1
    else:
        lines.append(build_entry(qid, src_text, orig_opts, orig_answer, orig_expl))
        NO_MATCH += 1

lines.append(']')

import shutil
shutil.copy(SRC, BACKUP)
print(f"Backed up to: {BACKUP}")

with open(OUT, 'w', encoding='utf-8', errors='replace') as f:
    f.write('\n'.join(lines))

print(f"Fixed (CA anchor): {FIXED}")
print(f"Failed (equal fallback): {FAILED}")
print(f"Skipped (already OK): {SKIPPED}")
print(f"No textbank match: {NO_MATCH}")
print(f"Total: {FIXED + FAILED + SKIPPED + NO_MATCH}")
print(f"Written: {OUT}")
