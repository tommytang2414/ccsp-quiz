'use client'

import { useQuizStore } from '@/lib/quiz-store'

export default function QuizPage() {
  const {
    mode, loadState,
    current, selected, confirmed,
    totalAnswered, totalCorrect,
    sessionCorrect, sessionAnswered,
    wrongCount,
    startQuiz, answer, next, goHome, resetProgress,
    questions,
  } = useQuizStore()

  if (loadState === 'loading') {
    return (
      <main className="min-h-dvh flex items-center justify-center">
        <p className="text-slate-500 text-sm">Loading...</p>
      </main>
    )
  }

  if (mode === 'home') return <HomeScreen
    wrongCount={wrongCount}
    totalAnswered={totalAnswered}
    totalCorrect={totalCorrect}
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
      onAnswer={answer}
      onNext={next}
      onHome={goHome}
    />
  )

  return null
}

function HomeScreen({
  wrongCount, totalAnswered, totalCorrect, total,
  onStart, onWrongOnly, onReset,
}: {
  wrongCount: number
  totalAnswered: number
  totalCorrect: number
  total: number
  onStart: () => void
  onWrongOnly?: () => void
  onReset: () => void
}) {
  const remaining = total - totalAnswered
  const done = totalAnswered
  const pct = totalAnswered > 0 ? Math.round((totalCorrect / totalAnswered) * 100) : 0

  return (
    <main className="min-h-dvh flex flex-col items-center justify-center p-6 gap-8">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-slate-100 mb-2">CCSP Quiz</h1>
        <p className="text-slate-400">{total} questions</p>
      </div>

      {/* Progress bar */}
      <div className="w-full max-w-sm">
        <div className="flex justify-between text-xs text-slate-500 mb-1.5">
          <span>{done} done</span>
          <span>{remaining} remaining</span>
        </div>
        <div className="h-2 bg-slate-800/80 rounded-full overflow-hidden">
          <div
            className="h-full bg-indigo-600 rounded-full transition-all duration-300"
            style={{ width: `${total > 0 ? (done / total) * 100 : 0}%` }}
          />
        </div>
        {totalAnswered > 0 && (
          <p className="text-center text-sm text-slate-400 mt-2">
            Accuracy: <span className="text-slate-200 font-semibold">{pct}%</span> ({totalCorrect}/{totalAnswered})
          </p>
        )}
      </div>

      <div className="w-full max-w-sm space-y-3">
        {wrongCount > 0 && (
          <div className="bg-red-900/30 border border-red-800/50 rounded-2xl p-5 text-center">
            <p className="text-red-400 text-sm mb-1">Wrong answers stored</p>
            <p className="text-2xl font-bold text-red-300">{wrongCount} questions</p>
            <button
              onClick={onWrongOnly}
              className="mt-3 w-full bg-red-900/50 hover:bg-red-800/60 text-red-200 font-medium py-2.5 rounded-xl transition-colors text-sm"
            >
              Retry wrong ({wrongCount})
            </button>
          </div>
        )}

        <button
          onClick={onStart}
          className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-4 rounded-2xl transition-colors text-base"
        >
          {totalAnswered === 0 ? 'Start Quiz' : `Continue (${remaining} left)`}
        </button>

        {totalAnswered > 0 && (
          <button
            onClick={onReset}
            className="w-full bg-slate-800/60 hover:bg-slate-700/60 text-slate-400 font-medium py-3 rounded-2xl transition-colors text-sm"
          >
            Reset progress
          </button>
        )}
      </div>

      <p className="text-slate-600 text-xs text-center">
        Data synced to cloud — same progress on all devices
      </p>
    </main>
  )
}

function QuizScreen({
  question, selected, confirmed, answeredCount,
  onAnswer, onNext, onHome,
}: {
  question: { id: number; text: string; options: string[]; answer: number; explanation?: string }
  selected: number | null
  confirmed: boolean
  answeredCount: number
  onAnswer: (i: number) => void
  onNext: () => void
  onHome: () => void
}) {
  const letters = ['A', 'B', 'C', 'D', 'E']
  const isCorrect = selected !== null && selected === question.answer

  return (
    <main className="min-h-dvh flex flex-col p-4 max-w-lg mx-auto">
      <header className="flex items-center justify-between mb-4">
        <button
          onClick={onHome}
          className="text-slate-400 hover:text-slate-200 text-sm px-3 py-1.5 rounded-lg hover:bg-slate-800/60 transition-colors"
        >
          ← Home
        </button>
        <span className="text-slate-500 text-sm font-mono">#{question.id}</span>
      </header>

      <div className="flex-1 flex flex-col justify-center gap-5">
        <h2 className="text-xl font-semibold text-slate-100 leading-snug">
          {question.text}
        </h2>

        <div className="space-y-2.5">
          {question.options.map((opt, i) => {
            const isSelected = selected === i
            const isCorrectOpt = question.answer === i
            let bg = 'bg-slate-800/60 hover:bg-slate-700/60 border-slate-700/60'
            if (confirmed) {
              if (isCorrectOpt) bg = 'bg-emerald-900/50 border-emerald-600/60'
              else if (isSelected) bg = 'bg-red-900/50 border-red-600/60'
              else bg = 'bg-slate-800/30 border-slate-800/40'
            } else if (isSelected) {
              bg = 'bg-indigo-900/50 border-indigo-500/60'
            }
            return (
              <button
                key={i}
                onClick={() => onAnswer(i)}
                disabled={confirmed}
                className={`w-full text-left px-4 py-3.5 rounded-xl border transition-all text-sm font-medium ${bg}`}
              >
                <span className="text-slate-400 mr-2.5 font-mono text-xs">{letters[i]}</span>
                <span className="text-slate-200">{opt}</span>
              </button>
            )
          })}
        </div>

        {/* Explanation */}
        {confirmed && question.explanation && (
          <div className={`rounded-xl p-4 text-sm leading-relaxed ${isCorrect ? 'bg-emerald-900/30 border border-emerald-800/50' : 'bg-slate-800/60 border border-slate-700/60'}`}>
            <p className={`font-semibold mb-1 ${isCorrect ? 'text-emerald-300' : 'text-indigo-400'}`}>
              {isCorrect ? '✓ Correct' : '✗ Wrong'}
            </p>
            <p className="text-slate-300">{question.explanation}</p>
          </div>
        )}

        {confirmed && !question.explanation && (
          <div className={`rounded-xl p-4 text-sm ${isCorrect ? 'bg-emerald-900/30 border border-emerald-800/50' : 'bg-red-900/30 border border-red-800/50'}`}>
            <p className={`font-semibold ${isCorrect ? 'text-emerald-300' : 'text-red-300'}`}>
              {isCorrect ? '✓ Correct!' : `✗ Wrong — Answer: ${letters[question.answer]}`}
            </p>
          </div>
        )}

        {confirmed && (
          <div className="text-center mt-1">
            <button
              onClick={onNext}
              className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold px-10 py-3 rounded-xl transition-colors text-sm"
            >
              Next →
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
  wrongCount,
  onRetry, onWrongOnly, onHome,
  total,
}: {
  sessionCorrect: number
  sessionAnswered: number
  totalCorrect: number
  totalAnswered: number
  wrongCount: number
  onRetry: () => void
  onWrongOnly?: () => void
  onHome: () => void
  total: number
}) {
  const sessionPct = sessionAnswered > 0 ? Math.round((sessionCorrect / sessionAnswered) * 100) : 0
  const totalPct = totalAnswered > 0 ? Math.round((totalCorrect / totalAnswered) * 100) : 0
  const remaining = total - totalAnswered

  return (
    <main className="min-h-dvh flex flex-col items-center justify-center p-6 gap-8">
      <div className="text-center">
        <p className="text-slate-400 text-sm mb-2">Session complete</p>
        <p className="text-5xl font-bold text-slate-100">{sessionPct}%</p>
        <p className="text-slate-400 mt-1">{sessionCorrect}/{sessionAnswered} correct</p>
      </div>

      {totalAnswered > 0 && (
        <div className="bg-slate-800/60 rounded-2xl p-5 text-center w-full max-w-sm">
          <p className="text-slate-400 text-sm mb-1">All-time progress</p>
          <p className="text-xl font-bold text-slate-200">{totalPct}%</p>
          <p className="text-slate-500 text-sm">{totalCorrect}/{totalAnswered} correct · {remaining} remaining</p>
        </div>
      )}

      {wrongCount > 0 && (
        <div className="bg-red-900/30 border border-red-800/50 rounded-2xl p-4 text-center w-full max-w-sm">
          <p className="text-red-400 text-sm">{wrongCount} wrong answers stored</p>
        </div>
      )}

      <div className="w-full max-w-sm space-y-3">
        <button
          onClick={onRetry}
          className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-4 rounded-2xl transition-colors text-sm"
        >
          Random quiz again
        </button>

        {wrongCount > 0 && (
          <button
            onClick={onWrongOnly}
            className="w-full bg-red-900/40 hover:bg-red-800/50 border border-red-800/50 text-red-200 font-medium py-3.5 rounded-2xl transition-colors text-sm"
          >
            Retry wrong ({wrongCount})
          </button>
        )}

        <button
          onClick={onHome}
          className="w-full bg-slate-800/60 hover:bg-slate-700/60 text-slate-400 font-medium py-3 rounded-2xl transition-colors text-sm"
        >
          Home
        </button>
      </div>
    </main>
  )
}
