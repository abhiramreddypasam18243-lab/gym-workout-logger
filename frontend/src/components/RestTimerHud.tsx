import React, { useState, useEffect, useRef } from 'react'
import { Play, Pause, RotateCcw, Volume2, VolumeX, ChevronDown, ChevronUp, Plus, Minus, Timer } from 'lucide-react'
import { playMicroClick, playTimerEndSound, isSoundEnabled, setSoundEnabled } from '../utils/audio'

export const RestTimerHud: React.FC = () => {
  const [totalSeconds, setTotalSeconds] = useState(90)
  const [remainingSeconds, setRemainingSeconds] = useState(90)
  const [isRunning, setIsRunning] = useState(false)
  const [isExpanded, setIsExpanded] = useState(false)
  const [soundOn, setSoundOn] = useState(() => isSoundEnabled())
  const [justFinished, setJustFinished] = useState(false)

  const timerRef = useRef<number | null>(null)

  // Listen for global custom event 'titan-start-timer'
  useEffect(() => {
    const handleStartEvent = (e: Event) => {
      const custom = e as CustomEvent<{ seconds?: number }>
      const secs = custom.detail?.seconds || 90
      setTotalSeconds(secs)
      setRemainingSeconds(secs)
      setIsRunning(true)
      setIsExpanded(true)
      setJustFinished(false)
    }

    window.addEventListener('titan-start-timer', handleStartEvent)
    return () => window.removeEventListener('titan-start-timer', handleStartEvent)
  }, [])

  // Timer loop
  useEffect(() => {
    if (isRunning && remainingSeconds > 0) {
      timerRef.current = window.setTimeout(() => {
        setRemainingSeconds((prev) => {
          if (prev <= 1) {
            setIsRunning(false)
            setJustFinished(true)
            playTimerEndSound()
            return 0
          }
          return prev - 1
        })
      }, 1000)
    } else {
      if (timerRef.current) clearTimeout(timerRef.current)
    }

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [isRunning, remainingSeconds])

  const toggleSound = () => {
    const next = !soundOn
    setSoundOn(next)
    setSoundEnabled(next)
    if (next) playMicroClick()
  }

  const handleStart = () => {
    if (remainingSeconds === 0) {
      setRemainingSeconds(totalSeconds)
    }
    setIsRunning(true)
    setJustFinished(false)
    playMicroClick()
  }

  const handlePause = () => {
    setIsRunning(false)
    playMicroClick()
  }

  const handleReset = () => {
    setIsRunning(false)
    setRemainingSeconds(totalSeconds)
    setJustFinished(false)
    playMicroClick()
  }

  const handleSetPreset = (seconds: number) => {
    setTotalSeconds(seconds)
    setRemainingSeconds(seconds)
    setIsRunning(true)
    setJustFinished(false)
    playMicroClick()
  }

  const adjustSeconds = (delta: number) => {
    setRemainingSeconds((prev) => {
      const updated = Math.max(5, prev + delta)
      if (updated > totalSeconds) setTotalSeconds(updated)
      return updated
    })
    playMicroClick()
  }

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60)
    const s = secs % 60
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  }

  // Circular progress calculation
  const radius = 48
  const circumference = 2 * Math.PI * radius
  const progressRatio = totalSeconds > 0 ? remainingSeconds / totalSeconds : 0
  const strokeDashoffset = circumference - progressRatio * circumference

  return (
    <aside
      aria-label="Workout Rest Timer"
      style={{
        position: 'fixed',
        bottom: '1.25rem',
        right: '1.25rem',
        zIndex: 90,
        fontFamily: 'var(--font-sans)',
      }}
    >
      {/* Minimized Pill View */}
      {!isExpanded ? (
        <button
          type="button"
          onClick={() => {
            setIsExpanded(true)
            playMicroClick()
          }}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.625rem',
            padding: '0.625rem 1rem',
            background: isRunning
              ? 'var(--accent-primary-soft)'
              : 'var(--bg-surface)',
            border: isRunning
              ? '1px solid color-mix(in srgb, var(--accent-primary) 60%, transparent)'
              : '1px solid rgba(255, 255, 255, 0.12)',
            borderRadius: 'var(--radius-sm)',
            color: 'var(--text-main)',
            cursor: 'pointer',
            boxShadow: isRunning
              ? '0 8px 24px color-mix(in srgb, var(--accent-primary) 35%, transparent), 0 0 12px color-mix(in srgb, var(--accent-primary) 20%, transparent)'
              : '0 8px 20px rgba(0, 0, 0, 0.4)',
            transition: 'all 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
            transform: isRunning ? 'scale(1.02)' : 'none',
          }}
        >
          <div
            style={{
              width: '10px',
              height: '10px',
              borderRadius: '50%',
              background: isRunning ? 'var(--accent-primary)' : justFinished ? 'var(--accent-emerald)' : 'var(--text-dim)',
              boxShadow: isRunning ? 'none' : 'none',
              animation: isRunning ? 'pulseDot 1.5s infinite' : 'none',
            }}
          />
          <Timer size={16} style={{ color: isRunning ? 'var(--accent-primary)' : 'var(--text-muted)' }} />
          <span
            style={{
              fontFamily: 'var(--font-mono)',
              fontWeight: 700,
              fontSize: '0.9375rem',
              color: isRunning ? 'var(--accent-primary)' : 'var(--text-main)',
              letterSpacing: '-0.02em',
            }}
          >
            {formatTime(remainingSeconds)}
          </span>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
            {isRunning ? 'RESTING' : justFinished ? 'READY!' : 'REST'}
          </span>
          <ChevronUp size={16} style={{ color: 'var(--text-dim)', marginLeft: '2px' }} />
        </button>
      ) : (
        /* Expanded Floating Card View */
        <div
          className="card"
          style={{
            width: '320px',
            padding: '1.25rem',
            background: 'var(--bg-surface)',
            border: justFinished
              ? '1px solid color-mix(in srgb, var(--accent-emerald) 70%, transparent)'
              : isRunning
              ? '1px solid color-mix(in srgb, var(--accent-primary) 50%, transparent)'
              : '1px solid rgba(255, 255, 255, 0.12)',
            boxShadow: justFinished
              ? '0 16px 40px color-mix(in srgb, var(--accent-emerald) 25%, transparent), 0 0 20px color-mix(in srgb, var(--accent-emerald) 20%, transparent)'
              : '0 20px 48px rgba(0, 0, 0, 0.7), 0 0 24px color-mix(in srgb, var(--accent-primary) 15%, transparent)',
            borderRadius: 'var(--radius-sm)',
            animation: 'fadeInUp 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
          }}
        >
          {/* Header */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '1rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <div
                style={{
                  width: '28px',
                  height: '28px',
                  borderRadius: 'var(--radius-sm)',
                  background: isRunning ? 'color-mix(in srgb, var(--accent-primary) 20%, transparent)' : 'rgba(255, 255, 255, 0.06)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: isRunning ? 'var(--accent-primary)' : 'var(--text-muted)',
                }}
              >
                <Timer size={16} />
              </div>
              <span
                style={{
                  fontWeight: 700,
                  fontSize: '0.875rem',
                  letterSpacing: '0.04em',
                  textTransform: 'uppercase',
                  color: 'var(--text-main)',
                }}
              >
                Rest Interval Timer
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
              <button
                type="button"
                onClick={toggleSound}
                title={soundOn ? 'Mute Chime' : 'Enable Chime'}
                style={{
                  background: 'none',
                  border: 'none',
                  color: soundOn ? 'var(--accent-primary)' : 'var(--text-dim)',
                  cursor: 'pointer',
                  padding: '4px',
                  borderRadius: 'var(--radius-sm)',
                }}
              >
                {soundOn ? <Volume2 size={16} /> : <VolumeX size={16} />}
              </button>
              <button
                type="button"
                onClick={() => {
                  setIsExpanded(false)
                  playMicroClick()
                }}
                title="Minimize timer"
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-dim)',
                  cursor: 'pointer',
                  padding: '4px',
                  borderRadius: 'var(--radius-sm)',
                }}
              >
                <ChevronDown size={18} />
              </button>
            </div>
          </div>

          {/* Circular Countdown Ring */}
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              position: 'relative',
              margin: '0.75rem 0 1.25rem',
            }}
          >
            <svg width="128" height="128" viewBox="0 0 128 128" style={{ transform: 'rotate(-90deg)' }}>
              {/* Background track circle */}
              <circle
                cx="64"
                cy="64"
                r={radius}
                stroke="rgba(255, 255, 255, 0.08)"
                strokeWidth="7"
                fill="none"
              />
              {/* Animated Progress ring */}
              <circle
                cx="64"
                cy="64"
                r={radius}
                stroke={justFinished ? 'var(--accent-emerald)' : isRunning ? 'var(--accent-primary)' : 'var(--text-dim)'}
                strokeWidth="7"
                fill="none"
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
                style={{
                  transition: 'stroke-dashoffset 0.8s linear, stroke 0.3s ease',
                  filter: isRunning ? 'drop-shadow(0 0 6px color-mix(in srgb, var(--accent-primary) 60%, transparent))' : 'none',
                }}
              />
            </svg>

            {/* Centered Timer Text */}
            <div
              style={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                textAlign: 'center',
              }}
            >
              <div
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '1.875rem',
                  fontWeight: 800,
                  color: justFinished ? 'var(--accent-emerald)' : 'var(--text-main)',
                  lineHeight: 1,
                  letterSpacing: '-0.04em',
                }}
              >
                {formatTime(remainingSeconds)}
              </div>
              <div
                style={{
                  fontSize: '0.6875rem',
                  fontWeight: 700,
                  letterSpacing: '0.08em',
                  color: justFinished ? 'var(--accent-emerald)' : isRunning ? 'var(--accent-primary)' : 'var(--text-dim)',
                  marginTop: '4px',
                  textTransform: 'uppercase',
                }}
              >
                {justFinished ? 'READY TO LIFT!' : isRunning ? 'RECOVERING' : 'PAUSED'}
              </div>
            </div>
          </div>

          {/* Adjusters (-15s / +15s) */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.75rem',
              marginBottom: '1rem',
            }}
          >
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => adjustSeconds(-15)}
              style={{ padding: '0.25rem 0.625rem', height: '28px', fontSize: '0.75rem' }}
            >
              <Minus size={12} />
              <span>15s</span>
            </button>

            {isRunning ? (
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={handlePause}
                style={{ minWidth: '90px', borderColor: 'color-mix(in srgb, var(--accent-primary) 40%, transparent)' }}
              >
                <Pause size={14} />
                <span>Pause</span>
              </button>
            ) : (
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={handleStart}
                style={{ minWidth: '90px' }}
              >
                <Play size={14} />
                <span>{remainingSeconds === 0 ? 'Restart' : 'Resume'}</span>
              </button>
            )}

            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => adjustSeconds(15)}
              style={{ padding: '0.25rem 0.625rem', height: '28px', fontSize: '0.75rem' }}
            >
              <Plus size={12} />
              <span>15s</span>
            </button>

            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={handleReset}
              title="Reset"
              style={{ padding: '4px 8px', height: '28px' }}
            >
              <RotateCcw size={14} />
            </button>
          </div>

          {/* Quick Preset Buttons */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(5, 1fr)',
              gap: '0.375rem',
              borderTop: '1px solid rgba(255, 255, 255, 0.08)',
              paddingTop: '0.75rem',
            }}
          >
            {[30, 60, 90, 120, 180].map((sec) => (
              <button
                key={sec}
                type="button"
                onClick={() => handleSetPreset(sec)}
                style={{
                  background:
                    totalSeconds === sec && (isRunning || remainingSeconds === sec)
                      ? 'color-mix(in srgb, var(--accent-primary) 25%, transparent)'
                      : 'rgba(255, 255, 255, 0.04)',
                  border:
                    totalSeconds === sec && (isRunning || remainingSeconds === sec)
                      ? '1px solid color-mix(in srgb, var(--accent-primary) 50%, transparent)'
                      : '1px solid rgba(255, 255, 255, 0.06)',
                  borderRadius: 'var(--radius-sm)',
                  color:
                    totalSeconds === sec && (isRunning || remainingSeconds === sec)
                      ? 'var(--accent-primary)'
                      : 'var(--text-muted)',
                  fontSize: '0.6875rem',
                  fontWeight: 700,
                  padding: '4px 2px',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                {sec < 60 ? `${sec}s` : `${sec / 60}m`}
              </button>
            ))}
          </div>
        </div>
      )}
    </aside>
  )
}
