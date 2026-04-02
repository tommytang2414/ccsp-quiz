'use client'

const BIN_ID = 'ccsp-quiz'
const API_BASE = `https://api.jsonbin.io/v3/b/${BIN_ID}`
const MASTER_KEY = '$2a$10$D2SQeZLn2TTVk/hkEjVkEu0gl6nPJHcyWNytjQrRdMwXUMHGtC0vG'
const ACCESS_KEY = 'ccsp-quiz'

function getDeviceId(): string {
  if (typeof window === 'undefined') return 'server'
  let id = localStorage.getItem('ccsp-device-id')
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem('ccsp-device-id', id)
  }
  return id
}

export interface CloudData {
  wrongIds: number[]
  totalAnswered: number
  totalCorrect: number
  lastUpdated: number
}

export async function fetchCloudData(): Promise<CloudData | null> {
  try {
    const res = await fetch(`${API_BASE}/latest`, {
      headers: {
        'X-Access-Key': ACCESS_KEY,
        'X-Bin-Meta': 'false',
      },
      cache: 'no-store',
    })
    if (!res.ok) return null
    const json = await res.json()
    const data = json.record ?? json
    if (!data || typeof data.wrongIds === 'undefined') return null
    return data as CloudData
  } catch {
    return null
  }
}

export async function saveCloudData(data: CloudData): Promise<void> {
  try {
    await fetch(API_BASE, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'X-Access-Key': ACCESS_KEY,
        'X-Bin-Meta': 'false',
      },
      body: JSON.stringify(data),
    })
  } catch {
    // offline — will retry next save
  }
}
