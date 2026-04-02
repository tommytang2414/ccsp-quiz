'use client'

import { useQuizStore } from '@/lib/quiz-store'
import { useState } from 'react'

const SESSION_GOALS = [10, 20, 50, 100, 0]

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
  const store = useQuizStore()

  if (store.loadState === 'loading') {
    return (
      <main className="min-h-dvh flex items-center justify-center">
        <p className="loading-dots">Loading</p>
      </main>
    )
  }

  if (store.mode === 'login') return <LoginScreen store={store} />
  if (store.mode === 'home') return <HomeScreen store={store} />
  if (store.mode === 'done') return <DoneScreen store={store} />
  if (store.mode === 'quiz' && store.current) return <QuizScreen store={store} />
  return null
}

// ─── Login Screen ───────────────────────────────────────────────────────────

function LoginScreen({ store }: { store: ReturnType<typeof useQuizStore> }) {
  const [code, setCode] = useState('')

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (code.trim().length >= 4) {
      store.doRegister(code.trim().toUpperCase())
    }
  }

  return (
    <main className="min-h-dvh flex flex-col items-center justify-center p-6 gap-8">
      <div className="text-center">
        <div className="text-5xl mb-4">📝</div>
        <h1 className="text-3xl font-bold text-slate-100 mb-2">CCSP Quiz</h1>
        <p className="text-slate-500 text-sm">Enter your activation code to start</p>
      </div>

      <form onSubmit={handleSubmit} className="w-full max-w-xs space-y-4">
        <input
          type="text"
          value={code}
          onChange={e => setCode(e.target.value.toUpperCase())}
          placeholder="e.g. X7K2M9P3"
          maxLength={12}
          className="code-input"
          autoFocus
          autoComplete="off"
          spellCheck={false}
        />
        {store.loginError && (
          <p className="text-red-400 text-sm text-center">{store.loginError}</p>
        )}
        <button
          type="submit"
          disabled={store.isRegistering || code.trim().length < 4}
          className="start-btn w-full disabled:opacity-50"
        >
          {store.isRegistering ? 'Verifying...' : 'Activate'}
        </button>
      </form>

      <p className="text-slate-600 text-xs text-center max-w-xs">
        Get your code from the administrator.<br />One code = one account.
      </p>
    </main>
  )
}

// ─── Home Screen ────────────────────────────────────────────────────────────

function HomeScreen({ store }: { store: ReturnType<typeof useQuizStore> }) {
  const { wrongCount, totalAnswered, totalCorrect, sessionGoal, setSessionGoal,
          startQuiz, doLogout, resetProgress } = store
  const total = store.questions.length
  const done = totalAnswered
  const remaining = total - done
  const pct = done > 0 ? Math.round((totalCorrect / done) * 100) : 0
  const goalLabel = sessionGoal === 0 ? 'All' : `${sessionGoal}`

  return (
    <main className="min-h-dvh flex flex-col items-center justify-center p-6 gap-7">
      <div className="flex w-full max-w-sm justify-between items-start">
        <div>
          <p className="text-slate-500 text-sm">{getGreeting()}</p>
          <p className="text-slate-600 text-xs mt-1">CCSP Exam Prep</p>
        </div>
        <button onClick={doLogout} className="logout-btn">Sign out</button>
      </div>

      <div className="relative" style={{ width: 160, height: 160 }}>
        <ProgressRing pct={total > 0 ? (done / total) * 100 : 0} />
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-bold text-slate-100">{pct}%</span>
          <span className="text-xs text-slate-500">{done}/{total}</span>
        </div>
      </div>

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

      <div className="flex flex-col items-center gap-2">
        <p className="text-slate-500 text-xs">Questions per session</p>
        <div className="flex gap-2 flex-wrap justify-center">
          {SESSION_GOALS.map(g => {
            const label = g === 0 ? 'All' : `${g}`
            const active = sessionGoal === g
            return (
              <button key={g} onClick={() => setSessionGoal(g)}
                className={`goal-chip ${active ? 'active' : ''}`}>{label}</button>
            )
          })}
        </div>
      </div>

      {wrongCount > 0 && (
        <div className="wrong-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-red-300 font-semibold text-sm">{wrongCount} questions need review</p>
              <p className="text-red-400/60 text-xs mt-0.5">Focus on your weak areas</p>
            </div>
            <button onClick={() => startQuiz(true)} className="wrong-retry-btn">Practice</button>
          </div>
        </div>
      )}

      <button onClick={() => startQuiz(false)} className="start-btn">
        {done === 0 ? `Start · ${goalLabel} questions` : `Continue · ${goalLabel} questions`}
      </button>

      {done > 0 && (
        <button onClick={resetProgress} className="reset-link">Reset all progress</button>
      )}

      <p className="text-slate-600 text-xs">Synced across all your devices</p>
    </main>
  )
}

// ─── Quiz Screen ────────────────────────────────────────────────────────────

function QuizScreen({ store }: { store: ReturnType<typeof useQuizStore> }) {
  const { current, selected, confirmed, sessionAnswered, sessionGoal,
          answer, next, goHome } = store
  const letters = ['A', 'B', 'C', 'D', 'E']
  const isCorrect = selected !== null && current!.answer === selected
  const progress = sessionGoal > 0 ? sessionAnswered / sessionGoal : 0

  return (
    <main className="min-h-dvh flex flex-col max-w-lg mx-auto">
      <header className="flex items-center justify-between px-4 pt-4 pb-2">
        <button onClick={goHome} className="back-btn">✕</button>
        <div className="flex flex-col items-center">
          <span className="text-xs text-slate-500 font-mono">
            {sessionAnswered}{sessionGoal > 0 ? `/${sessionGoal}` : ''}
          </span>
          <span className="text-xs text-slate-600">Q#{current!.id}</span>
        </div>
        <div style={{ width: 40 }} />
      </header>

      <div className="px-4 pb-3">
        <div className="quiz-progress-track">
          <div className="quiz-progress-fill"
            style={{ width: `${Math.min(progress * 100, 100)}%` }} />
        </div>
      </div>

      <div className="flex-1 flex flex-col px-5 gap-5">
        <div className="flex-1 flex flex-col justify-center gap-5">
          <h2 className="question-text">{current!.text}</h2>

          <div className="options-list">
            {current!.options.map((opt, i) => {
              const isSelected = selected === i
              const isCorrectOpt = current!.answer === i
              let cls = 'option-btn'
              if (confirmed) {
                if (isCorrectOpt) cls += ' option-correct'
                else if (isSelected) cls += ' option-wrong'
                else cls += ' option-dim'
              } else if (isSelected) {
                cls += ' option-selected'
              }
              return (
                <button key={i} onClick={() => answer(i)} disabled={confirmed} className={cls}>
                  <span className="option-letter">{letters[i]}</span>
                  <span className="option-text">{opt}</span>
                </button>
              )
            })}
          </div>

          {confirmed && (
            <div className={`exp-box ${isCorrect ? 'exp-correct' : 'exp-wrong'}`}>
              <p className="exp-label">
                {isCorrect ? '✓ Correct!' : `✗ Answer: ${letters[current!.answer]}`}
              </p>
              {current!.explanation && (
                <p className="exp-text">{current!.explanation}</p>
              )}
            </div>
          )}
        </div>

        {confirmed && (
          <div className="pb-6 text-center">
            <button onClick={next} className="next-btn">
              {sessionAnswered >= sessionGoal && sessionGoal > 0 ? 'Finish' : 'Next →'}
            </button>
          </div>
        )}
      </div>
    </main>
  )
}

// ─── Done Screen ───────────────────────────────────────────────────────────

function DoneScreen({ store }: { store: ReturnType<typeof useQuizStore> }) {
  const { sessionCorrect, sessionAnswered, totalCorrect, totalAnswered,
          wrongCount, sessionGoal, startQuiz, doLogout, goHome } = store
  const total = store.questions.length
  const pct = sessionAnswered > 0 ? Math.round((sessionCorrect / sessionAnswered) * 100) : 0
  const stars = pct >= 90 ? 3 : pct >= 70 ? 2 : pct >= 50 ? 1 : 0
  const done = totalAnswered
  const remaining = total - done
  const totalPct = done > 0 ? Math.round((totalCorrect / done) * 100) : 0

  return (
    <main className="min-h-dvh flex flex-col items-center justify-center p-6 gap-6">
      <div className="flex gap-2">
        {[1,2,3].map(s => (
          <span key={s} className={`star ${s <= stars ? 'star-on' : 'star-off'}`}>★</span>
        ))}
      </div>

      <div className="text-center">
        <p className={`score-pct ${pct >= 70 ? 'score-good' : pct >= 50 ? 'score-ok' : 'score-bad'}`}>
          {pct}%
        </p>
        <p className="text-slate-400 text-sm">{sessionCorrect}/{sessionAnswered} correct</p>
        {sessionAnswered >= sessionGoal && sessionGoal > 0 && (
          <p className="text-emerald-400 text-xs mt-1">Session complete!</p>
        )}
      </div>

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

      <div className="w-full max-w-sm space-y-3">
        <button onClick={() => startQuiz(false)} className="start-btn w-full">Keep going</button>
        {wrongCount > 0 && (
          <button onClick={() => startQuiz(true)} className="wrong-retry-btn w-full">
            Review {wrongCount} wrong
          </button>
        )}
        <button onClick={goHome} className="reset-link w-full text-center">Back to home</button>
      </div>
    </main>
  )
}
