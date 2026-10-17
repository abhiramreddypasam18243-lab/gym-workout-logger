/**
 * Web Audio API synthesizer for satisfying tactile sound feedback.
 * No external MP3 files required — generates pure harmonic audio tones.
 */

let audioCtx: AudioContext | null = null

function getAudioContext(): AudioContext | null {
  if (typeof window === 'undefined') return null
  if (!audioCtx) {
    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext
    if (AudioContextClass) {
      audioCtx = new AudioContextClass()
    }
  }
  if (audioCtx && audioCtx.state === 'suspended') {
    audioCtx.resume().catch(() => {})
  }
  return audioCtx
}

let soundEnabled = true

export function setSoundEnabled(enabled: boolean) {
  soundEnabled = enabled
  try {
    localStorage.setItem('titan_sound_enabled', enabled ? 'true' : 'false')
  } catch {}
}

export function isSoundEnabled(): boolean {
  try {
    const val = localStorage.getItem('titan_sound_enabled')
    if (val !== null) return val === 'true'
  } catch {}
  return soundEnabled
}

/**
 * Play a satisfying soft chime when a set is marked complete
 */
export function playSetCompleteSound() {
  if (!isSoundEnabled()) return
  const ctx = getAudioContext()
  if (!ctx) return

  const now = ctx.currentTime

  // Tone 1: C5 (523.25 Hz)
  const osc1 = ctx.createOscillator()
  const gain1 = ctx.createGain()
  osc1.type = 'sine'
  osc1.frequency.setValueAtTime(523.25, now)
  gain1.gain.setValueAtTime(0.08, now)
  gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.18)
  osc1.connect(gain1)
  gain1.connect(ctx.destination)
  osc1.start(now)
  osc1.stop(now + 0.18)

  // Tone 2: G5 (783.99 Hz)
  const osc2 = ctx.createOscillator()
  const gain2 = ctx.createGain()
  osc2.type = 'sine'
  osc2.frequency.setValueAtTime(783.99, now + 0.08)
  gain2.gain.setValueAtTime(0.1, now + 0.08)
  gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.32)
  osc2.connect(gain2)
  gain2.connect(ctx.destination)
  osc2.start(now + 0.08)
  osc2.stop(now + 0.32)
}

/**
 * Play an energizing double chime when the rest timer reaches 00:00
 */
export function playTimerEndSound() {
  if (!isSoundEnabled()) return
  const ctx = getAudioContext()
  if (!ctx) return

  const now = ctx.currentTime

  // High fanfare chord: A5 (880 Hz) -> C#6 (1108 Hz) -> E6 (1318 Hz)
  const freqs = [880, 1108.73, 1318.51]
  freqs.forEach((freq, idx) => {
    const startTime = now + idx * 0.09
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.type = 'triangle'
    osc.frequency.setValueAtTime(freq, startTime)
    gain.gain.setValueAtTime(0.15, startTime)
    gain.gain.exponentialRampToValueAtTime(0.001, startTime + 0.4)
    osc.connect(gain)
    gain.connect(ctx.destination)
    osc.start(startTime)
    osc.stop(startTime + 0.4)
  })
}

/**
 * Play a subtle micro click when tapping buttons or presets
 */
export function playMicroClick() {
  if (!isSoundEnabled()) return
  const ctx = getAudioContext()
  if (!ctx) return

  const now = ctx.currentTime
  const osc = ctx.createOscillator()
  const gain = ctx.createGain()
  osc.type = 'sine'
  osc.frequency.setValueAtTime(1200, now)
  osc.frequency.exponentialRampToValueAtTime(400, now + 0.04)
  gain.gain.setValueAtTime(0.04, now)
  gain.gain.exponentialRampToValueAtTime(0.001, now + 0.04)
  osc.connect(gain)
  gain.connect(ctx.destination)
  osc.start(now)
  osc.stop(now + 0.04)
}
