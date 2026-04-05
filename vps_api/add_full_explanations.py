#!/usr/bin/env python3
"""
Extract full explanations from textbank and update questions.ts.
Current parser uses ([^.]+) which stops at first period — this extracts the full text.
"""

import re

TBANK = 'C:/Users/user/Downloads/CCSP questionbank.txt'
SRC = 'C:/Users/user/portfolio/ccsp-quiz/lib/questions.ts'
OUT = 'C:/Users/user/portfolio/ccsp-quiz/lib/questions.ts'
BACKUP = 'C:/Users/user/portfolio/ccsp-quiz/lib/questions_pre_fullexpl.ts'

with open(TBANK, 'r', encoding='utf-8', errors='replace') as f:
    raw = f.read()
with open(SRC, 'r', encoding='utf-8', errors='replace') as f:
    src_content = f.read()

# Build textbank index: qtext[:80] -> full explanation string
blocks = re.split(r'(?=Question#\d+Topic)', raw)
tb_index = {}  # key -> explanation text

for b in blocks[1:]:
    m_q = re.match(r'Question#\d+Topic', b)
    if not m_q:
        continue

    # Question text (up to ?)
    qmark = b.find('?')
    if qmark == -1:
        continue
    qtext = b[len(m_q.group(0)):qmark + 1].strip()
    qtext = re.sub(r'\s+', ' ', qtext)
    qtext = re.sub(r'^\d+\s+', '', qtext)

    # Extract full explanation
    expl_match = re.search(r'Explanation:\s*Correct answer:\s*(.+)', b, re.DOTALL)
    if not expl_match:
        continue

    full_expl = expl_match.group(1).strip()

    # Remove trailing reference lines like "(ISC)2 CCSP..." or "The Official (ISC)²..."
    # These look like: "(ISC)2 CCSP ... Pg \d+..." or "The Official (ISC)²..."
    full_expl = re.sub(r'\s*\(ISC\).{0,200}?Pg\s+[\d\-]+\.?', '', full_expl, flags=re.DOTALL)
    full_expl = re.sub(r'\s*The Official \(ISC\).{0,200}?Pg\s+[\d\-]+\.?', '', full_expl, flags=re.DOTALL)
    full_expl = re.sub(r'\s*\(ISC\)2 CCSP.+', '', full_expl, flags=re.DOTALL)

    # Clean up whitespace
    full_expl = re.sub(r'\s+', ' ', full_expl).strip()

    key = qtext[:80]
    if key not in tb_index:
        tb_index[key] = full_expl

print(f"Textbank entries indexed: {len(tb_index)}")

# Parse source questions
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
        'explanation': m.group(5)
    })

print(f"Source questions parsed: {len(src_questions)}")


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


UPDATED = 0
KEPT = 0
NOT_FOUND = 0

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

    key = src_text[:80]
    new_expl = tb_index.get(key)

    if new_expl and len(new_expl) > len(orig_expl):
        lines.append(build_entry(qid, src_text, orig_opts, orig_answer, new_expl))
        UPDATED += 1
    else:
        # Keep original (either not found or textbank version is shorter/same)
        lines.append(build_entry(qid, src_text, orig_opts, orig_answer, orig_expl))
        if new_expl:
            KEPT += 1
        else:
            NOT_FOUND += 1

lines.append(']')

# Backup original
import shutil
shutil.copy(SRC, BACKUP)
print(f"Backed up to: {BACKUP}")

with open(OUT, 'w', encoding='utf-8', errors='replace') as f:
    f.write('\n'.join(lines))

print(f"Updated: {UPDATED}, Kept original (same/shorter): {KEPT}, No textbank match: {NOT_FOUND}")
print(f"Written: {OUT}")
