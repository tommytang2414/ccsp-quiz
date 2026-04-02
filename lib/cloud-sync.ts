'use client'

// JSONBin.io — free, no auth needed for reading/writing
// Create a bin at https://jsonbin.io and replace BIN_ID below
// Both phone and desktop use the same BIN_ID = shared record
const BIN_ID = 'REPLACE_WITH_YOUR_JSONBIN_ID'
const API_BASE = `https://api.jsonbin.io/v3/b/${BIN_ID}`

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
      headers: { 'X-Bin-Meta': 'false' },
      cache: 'no-store',
    })
    if (!res.ok) return null
    const data = await res.json()
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
        'X-Bin-Meta': 'false',
      },
      body: JSON.stringify(data),
    })
  } catch {
    // offline — will retry next save
  }
}
