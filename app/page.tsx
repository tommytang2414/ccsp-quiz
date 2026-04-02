'use client'

import { useQuizStore } from '@/lib/quiz-store'
import { useEffect, useState } from 'react'

const SESSION_GOALS = [10, 20, 50, 100, 0] // 0 = all

function getGreeting() {
  const h = new Date().getHours()
  if (h < 12) return 'Good morning ☀️'
  if (h < 18) return 'Good afternoon 👋'
  return 'Good evening 🌙'
}

function ProgressRing({ pct, size = 160, stroke = 12 }: { pct: number; size?: number; stroke?: number }) {
  const r = (size - stroke) / 2
  const circ = 2 * Math.PI * r
  const offset = circ - (pct / 100) * circ
  return (
    <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="rgba(51,65,85,0.6)" strokeWidth={stroke} />
      <circle
        cx={size/2} cy={size/2} r={r} fill="none"
        stroke="#818cf8" strokeWidth={stroke}
        strokeDasharray={circ}
        strokeDashoffset={offset}
        strokeLinecap="round"
        style={{ transition: 'stroke-dashoffset 0.6s ease' }}
      />
    </svg>
  )
}

export default function QuizPage() {
  const {
    mode, loadState,
    current, selected, confirmed,
    totalAnswered, totalCorrect,
    sessionCorrect, sessionAnswered,
    sessionGoal, setSessionGoal,
    wrongCount,
    startQuiz, answer, next, goHome, resetProgress,
    questions,
  } = useQuizStore()

  if (loadState === 'loading') {
    return (
      <main className="min-h-dvh flex items-center justify-center">
        <p className="loading-dots">Loading</p>
      </main>
    )
  }

  if (mode === 'home') return <HomeScreen
    wrongCount={wrongCount}
    totalAnswered={totalAnswered}
    totalCorrect={totalCorrect}
    sessionGoal={sessionGoal}
    onGoalChange={setSessionGoal}
    onStart={() => startQuiz(false)}
    onWrongOnly={() => wrongCount > 0 ? startQuiz(true) : undefined}
    onReset={resetProgress}
    total={questions.length}
  />

  if (mode === 'done') return <DoneScreen
    sessionCorrect={sessionCorrect}
    sessionAnswered={sessionAnswered}
    totalCorrect={totalCorrect}
    totalAnswered={totalAnswered}
    wrongCount={wrongCount}
    sessionGoal={sessionGoal}
    onRetry={() => startQuiz(false)}
    onWrongOnly={() => wrongCount > 0 ? startQuiz(true) : undefined}
    onHome={goHome}
    total={questions.length}
  />

  if (mode === 'quiz' && current) return (
    <QuizScreen
      question={current}
      selected={selected}
      confirmed={confirmed}
      answeredCount={sessionAnswered}
      sessionGoal={sessionGoal}
      onAnswer={answer}
      onNext={next}
      onHome={goHome}
    />
  )

  return null
}

function HomeScreen({
  wrongCount, totalAnswered, totalCorrect, total,
  sessionGoal, onGoalChange,
  onStart, onWrongOnly, onReset,
}: {
  wrongCount: number
  totalAnswered: number
  totalCorrect: number
  total: number
  sessionGoal: number
  onGoalChange: (g: number) => void
  onStart: () => void
  onWrongOnly?: () => void
  onReset: () => void
}) {
  const done = totalAnswered
  const remaining = total - done
  const pct = done > 0 ? Math.round((totalCorrect / done) * 100) : 0
  const goalLabel = sessionGoal === 0 ? 'All' : `${sessionGoal}`

  return (
    <main className="min-h-dvh flex flex-col items-center justify-center p-6 gap-7">
      <p className="text-slate-500 text-sm">{getGreeting()}</p>

      {/* Progress Ring */}
      <div className="relative" style={{ width: 160, height: 160 }}>
        <ProgressRing pct={total > 0 ? (done / total) * 100 : 0} />
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-bold text-slate-100">{pct}%</span>
          <span className="text-xs text-slate-500">{done}/{total}</span>
        </div>
      </div>

      {/* Stats row */}
      <div className="flex gap-6 text-center">
        <div>
          <div className="text-xl font-bold text-slate-200">{totalCorrect}</div>
          <div className="text-xs text-slate-500">correct</div>
        </div>
        <div className="w-px bg-slate-700" />
        <div>
          <div className="text-xl font-bold text-red-400">{wrongCount}</div>
          <div className="text-xs text-slate-500">to review</div>
        </div>
        <div className="w-px bg-slate-700" />
        <div>
          <div className="text-xl font-bold text-slate-200">{remaining}</div>
          <div className="text-xs text-slate-500">remaining</div>
        </div>
      </div>

      {/* Session goal picker */}
      <div className="flex flex-col items-center gap-2">
        <p className="text-slate-500 text-xs">Questions per session</p>
        <div className="flex gap-2 flex-wrap justify-center">
          {SESSION_GOALS.map(g => {
            const label = g === 0 ? 'All' : `${g}`
            const active = sessionGoal === g
            return (
              <button
                key={g}
                onClick={() => onGoalChange(g)}
                className={`goal-chip ${active ? 'active' : ''}`}
              >
                {label}
              </button>
            )
          })}
        </div>
      </div>

      {/* Wrong answers banner */}
      {wrongCount > 0 && (
        <div className="wrong-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-red-300 font-semibold text-sm">{wrongCount} questions need review</p>
              <p className="text-red-400/60 text-xs mt-0.5">Focus on your weak areas</p>
            </div>
            <button onClick={onWrongOnly} className="wrong-retry-btn">
              Practice
            </button>
          </div>
        </div>
      )}

      {/* Main CTA */}
      <button onClick={onStart} className="start-btn">
        {done === 0 ? `Start · ${goalLabel} questions` : `Continue · ${goalLabel} questions`}
      </button>

      {done > 0 && (
        <button onClick={onReset} className="reset-link">
          Reset all progress
        </button>
      )}

      <p className="text-slate-600 text-xs">Synced across all your devices</p>
    </main>
  )
}

function QuizScreen({
  question, selected, confirmed, answeredCount, sessionGoal,
  onAnswer, onNext, onHome,
}: {
  question: { id: number; text: string; options: string[]; answer: number; explanation?: string }
  selected: number | null
  confirmed: boolean
  answeredCount: number
  sessionGoal: number
  onAnswer: (i: number) => void
  onNext: () => void
  onHome: () => void
}) {
  const letters = ['A', 'B', 'C', 'D', 'E']
  const isCorrect = selected !== null && selected === question.answer
  const progress = sessionGoal > 0 ? answeredCount / sessionGoal : 0

  return (
    <main className="min-h-dvh flex flex-col max-w-lg mx-auto">
      {/* Header */}
      <header className="flex items-center justify-between px-4 pt-4 pb-2">
        <button onClick={onHome} className="back-btn">✕</button>
        <div className="flex flex-col items-center">
          <span className="text-xs text-slate-500 font-mono">
            {answeredCount}{sessionGoal > 0 ? `/${sessionGoal}` : ''}
          </span>
          <span className="text-xs text-slate-600">Q#{question.id}</span>
        </div>
        <div style={{ width: 40 }} />
      </header>

      {/* Progress bar */}
      <div className="px-4 pb-3">
        <div className="quiz-progress-track">
          <div
            className="quiz-progress-fill"
            style={{ width: `${Math.min(progress * 100, 100)}%` }}
          />
        </div>
      </div>

      {/* Question */}
      <div className="flex-1 flex flex-col px-5 gap-5">
        <div className="flex-1 flex flex-col justify-center gap-5">
          <h2 className="question-text">{question.text}</h2>

          <div className="options-list">
            {question.options.map((opt, i) => {
              const isSelected = selected === i
              const isCorrectOpt = question.answer === i
              let cls = 'option-btn'
              if (confirmed) {
                if (isCorrectOpt) cls += ' option-correct'
                else if (isSelected) cls += ' option-wrong'
                else cls += ' option-dim'
              } else if (isSelected) {
                cls += ' option-selected'
              }
              return (
                <button key={i} onClick={() => onAnswer(i)} disabled={confirmed} className={cls}>
                  <span className="option-letter">{letters[i]}</span>
                  <span className="option-text">{opt}</span>
                </button>
              )
            })}
          </div>

          {/* Explanation */}
          {confirmed && (
            <div className={`exp-box ${isCorrect ? 'exp-correct' : 'exp-wrong'}`}>
              <p className="exp-label">
                {isCorrect ? '✓ Correct!' : `✗ Answer: ${letters[question.answer]}`}
              </p>
              {question.explanation && (
                <p className="exp-text">{question.explanation}</p>
              )}
            </div>
          )}
        </div>

        {confirmed && (
          <div className="pb-6 text-center">
            <button onClick={onNext} className="next-btn">
              {answeredCount >= sessionGoal && sessionGoal > 0 ? 'Finish' : 'Next →'}
            </button>
          </div>
        )}
      </div>
    </main>
  )
}

function DoneScreen({
  sessionCorrect, sessionAnswered,
  totalCorrect, totalAnswered,
  wrongCount, sessionGoal,
  onRetry, onWrongOnly, onHome,
  total,
}: {
  sessionCorrect: number
  sessionAnswered: number
  totalCorrect: number
  totalAnswered: number
  wrongCount: number
  sessionGoal: number
  onRetry: () => void
  onWrongOnly?: () => void
  onHome: () => void
  total: number
}) {
  const pct = sessionAnswered > 0 ? Math.round((sessionCorrect / sessionAnswered) * 100) : 0
  const stars = pct >= 90 ? 3 : pct >= 70 ? 2 : pct >= 50 ? 1 : 0
  const done = totalAnswered
  const remaining = total - done
  const totalPct = done > 0 ? Math.round((totalCorrect / done) * 100) : 0

  return (
    <main className="min-h-dvh flex flex-col items-center justify-center p-6 gap-6">
      {/* Stars */}
      <div className="flex gap-2">
        {[1,2,3].map(s => (
          <span key={s} className={`star ${s <= stars ? 'star-on' : 'star-off'}`}>
            ★
          </span>
        ))}
      </div>

      {/* Score */}
      <div className="text-center">
        <p className={`score-pct ${pct >= 70 ? 'score-good' : pct >= 50 ? 'score-ok' : 'score-bad'}`}>
          {pct}%
        </p>
        <p className="text-slate-400 text-sm">{sessionCorrect}/{sessionAnswered} correct</p>
        {sessionAnswered >= sessionGoal && sessionGoal > 0 && (
          <p className="text-emerald-400 text-xs mt-1">Session complete!</p>
        )}
      </div>

      {/* All-time stats */}
      <div className="alltime-card">
        <p className="text-slate-400 text-xs mb-2">All-time progress</p>
        <div className="flex gap-6 text-center">
          <div>
            <div className="text-lg font-bold text-slate-200">{totalPct}%</div>
            <div className="text-xs text-slate-500">accuracy</div>
          </div>
          <div className="w-px bg-slate-700" />
          <div>
            <div className="text-lg font-bold text-slate-200">{done}/{total}</div>
            <div className="text-xs text-slate-500">attempted</div>
          </div>
          <div className="w-px bg-slate-700" />
          <div>
            <div className="text-lg font-bold text-red-400">{wrongCount}</div>
            <div className="text-xs text-slate-500">to review</div>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="w-full max-w-sm space-y-3">
        <button onClick={onRetry} className="start-btn w-full">
          Keep going
        </button>

        {wrongCount > 0 && (
          <button onClick={onWrongOnly} className="wrong-retry-btn w-full">
            Review {wrongCount} wrong
          </button>
        )}

        <button onClick={onHome} className="reset-link w-full text-center">
          Back to home
        </button>
      </div>
    </main>
  )
}
