# CCSP Quiz App

Mobile-first quiz app for CCSP exam preparation.

## Stack
- Next.js 14 (Pages Router equivalent via app dir with 'use client')
- Pure CSS (no Tailwind)
- localStorage for wrong-answer persistence
- PWA (installable on mobile)

## Run
```bash
cd C:/Users/user/portfolio/ccsp-quiz
npm run dev
```

## Questions
100 MCQs from `CCSP-PP Exam_061120251498.pdf`. Sourced from Q1-Q66 and Q68-Q101 (skip image-based questions).

## Features
- Random quiz (no repeats within a session)
- Wrong-answer tracking (persisted in localStorage)
- Retry-wrong-only mode
- All-time progress stats
- Dark mode UI
- PWA installable
