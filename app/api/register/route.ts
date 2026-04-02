import { NextRequest, NextResponse } from 'next/server'

const VPS_API = 'http://18.139.210.59:5001'

export async function POST(req: NextRequest) {
  const body = await req.json()
  const { code, exam } = body

  if (!code || code.length < 4) {
    return NextResponse.json({ error: 'Invalid code' }, { status: 400 })
  }

  try {
    const res = await fetch(`${VPS_API}/api/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, exam }),
    })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (e) {
    return NextResponse.json({ error: 'Server error' }, { status: 500 })
  }
}
