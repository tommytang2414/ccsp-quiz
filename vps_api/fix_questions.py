#!/usr/bin/env python3
"""Fix CCSP question options — match by question text, fix only confirmed corruptions."""

import re

TBANK = 'C:/Users/user/Downloads/CCSP questionbank.txt'
SRC = 'C:/Users/user/portfolio/ccsp-quiz/lib/questions.ts'
OUT = 'C:/Users/user/portfolio/ccsp-quiz/lib/questions_fixed.ts'

FRAGMENTS = {
    'Security', 'Function', 'Isolation', 'Boundary', 'Protection',
    'Key', 'Establishment', 'Management', 'Account', 'Logging',
    'In', 'On', 'To', 'For', 'Of', 'The', 'And', 'Or', 'Is', 'Are',
    'With', 'From', 'That', 'This', 'Not', 'Can', 'Be', 'May',
    'They', 'Their', 'Them', 'This', 'That', 'These', 'Those',
    'Must', 'Should', 'Could', 'Would', 'Will', 'Shall', 'May', 'Might',
    'API', 'SaaS', 'PaaS', 'IaaS', 'FaaS', 'VPC', 'VPN', 'DNS',
    'SIEM', 'IAM', 'RBAC', 'OAuth', 'SAML', 'SSO', 'MFA',
    'CSP', 'CSC', 'PII', 'PHI', 'PCI', 'DSS', 'GDPR',
    'ISO', 'NIST', 'FIPS', 'FedRAMP', 'CSA', 'STAR', 'CSF',
}


def all_splits(n):
    result = []
    for s1 in range(1, n - 2):
        for s2 in range(s1 + 1, n - 1):
            for s3 in range(s2 + 1, n):
                result.append([s1, s2, s3])
    return result


def ca_anchor_pos(words, ca_text, n):
    ca_words = ca_text.lower().split()
    if not ca_words:
        return -1
    best = None
    for n_try in range(1, min(7, len(ca_words) + 1)):
        anchor = ' '.join(ca_words[:n_try])
        for start in range(n - n_try + 1):
            seg = ' '.join(words[start:start + n_try]).lower()
            if seg == anchor:
                extra = 0
                limit = len(ca_words) - n_try
                remaining = n - start - n_try
                for j in range(min(limit, remaining)):
                    if words[start + n_try + j].lower() == ca_words[n_try + j]:
                        extra += 1
                    else:
                        break
                conf = n_try * 10 + extra
                if best is None or conf > best[2]:
                    best = (start, n_try, conf)
    return best[0] if best else -1


def smart_fix(words, n, ca_text, answer_idx):
    """Try to find a split where the correct option starts with the CA text."""
    if n < 4:
        return None
    ca_pos = ca_anchor_pos(words, ca_text, n)
    if ca_pos < 0:
        return None
    # Use only first 4 words of CA as anchor (answers are typically 2-6 words)
    ca_words_limited = ca_text.lower().split()[:4]
    ca_first = ca_words_limited[0]
    ca_len = len(ca_words_limited)
    best = None
    best_score = float('inf')
    for sp in all_splits(n):
        splits = [0] + sp + [n]
        if splits[answer_idx] <= ca_pos < splits[answer_idx + 1]:
            opt_words = words[splits[answer_idx]:splits[answer_idx + 1]]
            opt_text = ' '.join(opt_words).lower()
            # Option must START with the CA anchor (not just contain it)
            if not opt_text.startswith(ca_first):
                continue
            # Also verify the first ca_len words match
            if len(opt_words) < ca_len:
                continue
            match = all(opt_words[k].lower() == ca_words_limited[k] for k in range(ca_len))
            if not match:
                continue
            lens = [splits[i + 1] - splits[i] for i in range(4)]
            bal = max(lens) - min(lens)
            # Prefer answer option to be reasonably sized (at least 3 words, not too large)
            ans_size = lens[answer_idx]
            size_penalty = max(0, ans_size - 12) * 2 + max(0, 3 - ans_size) * 3
            score = bal + size_penalty
            if best is None or score < best_score:
                best_score = score
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


def has_fragment(opts):
    if len(opts) != 4:
        return False
    for o in opts:
        w = o.split()
        if not w:
            return True  # empty option = corruption
        if len(w) == 1 and w[0].lower() in {f.lower() for f in FRAGMENTS}:
            return True
    return False


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


# MAIN
with open(SRC, 'r', encoding='utf-8', errors='replace') as f:
    src_content = f.read()
with open(TBANK, 'r', encoding='utf-8', errors='replace') as f:
    raw = f.read()

# Parse source questions in order
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

print('Source questions: {}'.format(len(src_questions)))

# Parse textbank blocks
blocks = re.split(r'(?=Question#\d+Topic)', raw)
tb_questions = []
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
    qtext = re.sub(r'^\d+\s+', '', qtext)  # strip leading topic number
    tb_questions.append({
        'block': b,
        'text': qtext,
        'answer_idx': ord(m_ca.group(1)) - ord('A'),
        'ca_text': m_expl.group(1).strip()
    })

print('Textbank entries: {}'.format(len(tb_questions)))

# Build text-to-block index (first 80 chars for matching)
tb_index = {}
for i, tq in enumerate(tb_questions):
    key = tq['text'][:80]
    if key not in tb_index:
        tb_index[key] = []
    tb_index[key].append(i)

# Match source questions to textbank by text
OK, FIXED, MISSING = 0, 0, 0
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
    orig_opts = [o.strip().strip('"') for o in src['opts_str'].split('",')]
    src_text = src['text']

    # Find matching textbank entry
    key = src_text[:80]
    matches = tb_index.get(key, [])

    if not matches:
        lines.append(build_entry(qid, src_text, orig_opts, src['answer'], src['explanation']))
        MISSING += 1
        continue

    tq = tb_questions[matches[0]]
    block = tq['block']
    answer_idx = tq['answer_idx']
    ca_text = tq['ca_text']

    qmark = block.find('?')
    m_q = re.match(r'Question#\d+Topic', block)
    qtext = block[len(m_q.group(0)):qmark + 1].strip()
    qtext = re.sub(r'\s+', ' ', qtext)
    qtext = re.sub(r'^\d+\s+', '', qtext)

    opts_raw = block[qmark + 1:re.search(r'Correct Answer:', block).start()].strip()
    opts_raw = re.sub(r'xmexam\.taobao\.com\s*', '', opts_raw).strip()
    words = opts_raw.split()
    n = len(words)

    if has_fragment(orig_opts):
        candidate = smart_fix(words, n, ca_text, answer_idx) if n >= 4 else None
        if candidate and not has_fragment(candidate):
            opts = candidate
            FIXED += 1
        else:
            opts = equal_part(words, n) if n >= 4 else orig_opts
            FIXED += 1
    else:
        opts = orig_opts
        OK += 1

    explanation = ca_text.lstrip(',').strip() or src['explanation'].lstrip(',').strip()
    lines.append(build_entry(qid, qtext, opts, answer_idx, explanation))

lines.append(']')
with open(OUT, 'w', encoding='utf-8', errors='replace') as f:
    f.write('\n'.join(lines))

print('Unchanged: {}, Fixed: {}, Missing: {}'.format(OK, FIXED, MISSING))
print('Written:', OUT)
