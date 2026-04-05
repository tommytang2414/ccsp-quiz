#!/usr/bin/env python3
"""Re-parse CCSP questionbank.txt fixing corrupted options."""

import re

TBANK = 'C:/Users/user/Downloads/CCSP questionbank.txt'
OUTPUT = 'C:/Users/user/portfolio/ccsp-quiz/lib/questions_new.ts'

with open(TBANK, 'r', encoding='utf-8', errors='replace') as f:
    raw = f.read()

blocks = re.split(r'(?=Question#\d+Topic)', raw)
print(f"Total blocks: {len(blocks)-1}")

OK = 0
CORRUPT = 0
output_lines = ["export interface Question {",
    "  id: number",
    "  text: string",
    "  options: string[]",
    "  answer: number // 0-based index",
    "  explanation?: string",
    "}\n",
    "export const questions: Question[] = ["]
qid_counter = 1

# Fragments that indicate corruption
FRAGMENTS = {'Security', 'Function', 'Isolation', 'Boundary', 'Protection',
              'Key', 'Establishment', 'Management', 'Account', 'Use', 'Logging',
              'Cloud', 'Service', 'Customer', 'Provider', 'Partner', 'Broker',
              'In', 'On', 'To', 'For', 'Of', 'The', 'And', 'Or'}

for block in blocks[1:]:
    qmatch = re.match(r'Question#(\d+)Topic', block)
    if not qmatch:
        continue

    ca_match = re.search(r'Correct Answer: ([A-Z])', block)
    expl_match = re.search(r'Explanation:\s*Correct answer:\s*([^.]+)', block)
    if not ca_match or not expl_match:
        continue

    answer_letter = ca_match.group(1)
    answer_idx = ord(answer_letter) - ord('A')
    correct_text = expl_match.group(1).strip()
    ca_words = correct_text.lower().split()

    # Question text
    qmark = block.find('?')
    if qmark == -1:
        continue
    question_text = block[len(qmatch.group(0)):qmark+1].strip()
    question_text = re.sub(r'\s+', ' ', question_text)

    # Options raw
    options_raw = block[qmark+1:ca_match.start()].strip()
    options_raw = re.sub(r'xmexam\.taobao\.com\s*', '', options_raw).strip()
    words = options_raw.split()
    n = len(words)

    # Partition into 4 options
    opts = partition_words(words, n, ca_words)

    # Check if clean
    is_clean = (n >= 4 and n <= 8 and
                all(len(o.split()) >= 2 for o in opts) and
                len(opts) == 4 and
                not any(len(o.split()) == 1 and o in FRAGMENTS for o in opts))

    if is_clean:
        OK += 1
    else:
        CORRUPT += 1

    # Format explanation
    explanation = correct_text
    if explanation.startswith(','):
        explanation = explanation[1:].strip()

    # Build entry
    opts_escaped = [o.replace('"', '\\"') for o in opts]
    text_escaped = question_text.replace('"', '\\"')
    expl_escaped = explanation.replace('"', '\\"')
    entry = f"""  {{
    id: {qid_counter},
    text: "{text_escaped}",
    options: ["{'", "'.join(opts_escaped)}"],
    answer: {answer_idx},
    explanation: "{expl_escaped}",
  }},"""
    output_lines.append(entry)
    qid_counter += 1

output_lines.append("]")
with open(OUTPUT, 'w', encoding='utf-8') as f:
    f.write('\n'.join(output_lines))

print(f"Clean: {OK}, Corrupt: {CORRUPT}")
print(f"Output: {OUTPUT}")


def ca_in_option(option_text, ca_words_list):
    """Check if option text starts with the correct answer words."""
    opt_lower = option_text.lower()
    opt_words = opt_lower.split()
    if len(ca_words_list) > len(opt_words):
        return False
    return opt_words[:len(ca_words_list)] == ca_words_list


def partition_words(words, n, ca_words):
    """Smart partition of words into 4 options."""
    if n == 4:
        return words

    # Try equal partition (for n=8,16,etc) with answer as anchor
    # n=8: try 2+2+2+2
    # n=12: try 3+3+3+3 or 2+3+3+4
    # n=16: try 4+4+4+4 or 3+4+4+5 etc

    best = None

    # Try all 3-split-point combinations
    for s1 in range(1, n):
        for s2 in range(s1+1, n):
            for s3 in range(s2+1, n):
                p1 = words[:s1]
                p2 = words[s1:s2]
                p3 = words[s2:s3]
                p4 = words[s3:]
                opts_cand = [' '.join(p) for p in [p1, p2, p3, p4]]

                # Skip if any option is a single fragment
                if any(len(o.split()) == 1 and o in FRAGMENTS for o in opts_cand):
                    continue

                # Check if correct answer is in the right option
                if ca_in_option(opts_cand[ord(ca_match.group(1)) - ord('A')], ca_words):
                    if best is None or max(len(p) for p in [p1,p2,p3,p4]) - min(len(p) for p in [p1,p2,p3,p4]) < max(len(p) for p in [w.split() for w in best] if best else [n,n,n,n]) - min(len(p) for p in [w.split() for w in best] if best else [n,n,n,n]):
                        best = opts_cand

    if best:
        return best

    # Fallback: equal partition
    q, r = divmod(n, 4)
    parts = [q] * 4
    for i in range(r):
        parts[i] += 1
    splits = [0]
    acc = 0
    for p in parts:
        acc += p
        splits.append(acc)
    return [' '.join(words[splits[i]:splits[i+1]]) for i in range(4)]
