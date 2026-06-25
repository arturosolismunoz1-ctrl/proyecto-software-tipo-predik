// Vercel Serverless Function — mantiene el backend de Render despierto
// Se ejecuta cada 10 minutos via vercel.json crons
export default async function handler(req, res) {
  try {
    const r = await fetch(
      'https://proyecto-software-tipo-predik.onrender.com/health',
      { signal: AbortSignal.timeout(30000) }
    )
    res.status(200).json({ ok: true, backend: r.status, ts: new Date().toISOString() })
  } catch (e) {
    res.status(200).json({ ok: false, error: e.message, ts: new Date().toISOString() })
  }
}
