'use client'

import { useState, useEffect, useCallback } from 'react'
import { questions, Question } from './questions'
import { fetchCloudData, saveCloudData } from './cloud-sync'

type QuizMode = 'home' | 'quiz' | 'done'
type LoadState = 'loading' | 'ready' | 'error'

function shuffle<T>(arr: T[]): T[] {
  const a = [...arr]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

export function useQuizStore() {
  const [mode, setMode] = useState<QuizMode>('home')
  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [wrongIds, setWrongIds] = useState<Set<number>>(new Set())
  const [queue, setQueue] = useState<Question[]>([])
  const [current, setCurrent] = useState<Question | null>(null)
  const [selected, setSelected] = useState<number | null>(null)
  const [confirmed, setConfirmed] = useState(false)
  const [totalAnswered, setTotalAnswered] = useState(0)
  const [totalCorrect, setTotalCorrect] = useState(0)
  const [sessionCorrect, setSessionCorrect] = useState(0)
  const [sessionAnswered, setSessionAnswered] = useState(0)
  const [sessionGoal, setSessionGoal] = useState(20)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      const cloud = await fetchCloudData()
      if (cancelled) return
      if (cloud) {
        setWrongIds(new Set(cloud.wrongIds))
        setTotalAnswered(cloud.totalAnswered)
        setTotalCorrect(cloud.totalCorrect)
      }
      setLoadState('ready')
    })()
    return () => { cancelled = true }
  }, [])

  const startQuiz = useCallback((wrongOnly = false) => {
    const src = wrongOnly && wrongIds.size > 0
      ? questions.filter(q => wrongIds.has(q.id))
      : questions
    const shuffled = shuffle(src)
    // Limit to sessionGoal questions
    const limited = shuffled.slice(0, sessionGoal)
    setQueue(limited)
    setCurrent(limited[0] ?? null)
    setSelected(null)
    setConfirmed(false)
    setSessionCorrect(0)
    setSessionAnswered(0)
    setMode('quiz')
  }, [wrongIds, sessionGoal])

  const answer = useCallback((optIndex: number) => {
    if (confirmed) return
    setSelected(optIndex)
    setConfirmed(true)
    const correct = current!.answer === optIndex
    const nextAnswered = totalAnswered + 1
    const nextCorrect = correct ? totalCorrect + 1 : totalCorrect
    const nextWrong = new Set(wrongIds)
    if (correct) {
      nextWrong.delete(current!.id)
    } else {
      nextWrong.add(current!.id)
    }
    setTotalAnswered(nextAnswered)
    setTotalCorrect(nextCorrect)
    setSessionAnswered(a => a + 1)
    setSessionCorrect(c => c + (correct ? 1 : 0))
    setWrongIds(nextWrong)
    saveCloudData({
      wrongIds: [...nextWrong],
      totalAnswered: nextAnswered,
      totalCorrect: nextCorrect,
      lastUpdated: Date.now(),
    })
  }, [confirmed, current, wrongIds, totalAnswered, totalCorrect])

  const next = useCallback(() => {
    const idx = queue.indexOf(current!)
    if (idx + 1 >= queue.length) {
      setMode('done')
    } else {
      setCurrent(queue[idx + 1])
      setSelected(null)
      setConfirmed(false)
    }
  }, [current, queue])

  const goHome = useCallback(() => {
    setMode('home')
    setCurrent(null)
  }, [])

  const resetProgress = useCallback(async () => {
    setWrongIds(new Set())
    setTotalAnswered(0)
    setTotalCorrect(0)
    await saveCloudData({ wrongIds: [], totalAnswered: 0, totalCorrect: 0, lastUpdated: Date.now() })
  }, [])

  const wrongCount = wrongIds.size

  return {
    mode, loadState,
    current, selected, confirmed,
    totalAnswered, totalCorrect,
    sessionCorrect, sessionAnswered,
    sessionGoal, setSessionGoal,
    wrongCount,
    startQuiz, answer, next, goHome, resetProgress,
    questions,
  }
}
