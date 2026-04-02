'use client'

// API routes via Next.js (same origin on Vercel)
// No more CORS/mixed-content issues
const API = '/api'

export interface CloudData {
  wrongIds: number[]
  totalAnswered: number
  totalCorrect: number
  lastUpdated: number
}

export async function register(code: string, exam = 'CCSP'): Promise<{ token: string; userId: string }> {
  const res = await fetch(`${API}/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code, exam }),
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.error || 'Invalid code')
  localStorage.setItem('ccsp-auth-token', data.token)
  localStorage.setItem('ccsp-exam', data.exam || exam)
  return { token: data.token, userId: data.userId }
}

export function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('ccsp-auth-token')
}

export function logout(): void {
  localStorage.removeItem('ccsp-auth-token')
  localStorage.removeItem('ccsp-exam')
}

export async function fetchCloudData(): Promise<CloudData | null> {
  const token = getToken()
  if (!token) return null
  try {
    const res = await fetch(`${API}/data`, {
      headers: { 'Authorization': `Bearer ${token}` },
      cache: 'no-store',
    })
    if (!res.ok) return null
    const json = await res.json()
    const data = json.data ?? json
    if (!data || typeof data.wrongIds === 'undefined') return null
    return data as CloudData
  } catch {
    return null
  }
}

export async function saveCloudData(data: CloudData): Promise<void> {
  const token = getToken()
  if (!token) return
  try {
    await fetch(`${API}/data`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(data),
    })
  } catch {
    // offline — will retry next save
  }
}
