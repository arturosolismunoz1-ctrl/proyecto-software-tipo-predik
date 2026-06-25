// Edge Function — mantiene Render despierto (timeout 30s en Edge vs 10s en Serverless)
export const config = { runtime: 'edge' }

export default async function handler() {
  try {
    const r = await fetch(
      'https://proyecto-software-tipo-predik.onrender.com/health',
      { signal: AbortSignal.timeout(25000) }
    )
    const body = { ok: true, backend: r.status, ts: new Date().toISOString() }
    return Response.json(body)
  } catch (e) {
    return Response.json({ ok: false, error: e.message, ts: new Date().toISOString() })
  }
}
