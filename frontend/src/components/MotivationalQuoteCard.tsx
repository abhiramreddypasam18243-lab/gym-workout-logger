import React, { useState } from 'react'
import { Sparkles, RefreshCw, Copy, Check, Flame, Award, Dumbbell, Compass, Heart } from 'lucide-react'
import { getRandomQuote, getDailyQuote, type MotivationalQuote } from '../utils/quotes'
import { playMicroClick } from '../utils/audio'

interface MotivationalQuoteCardProps {
  variant?: 'hero' | 'compact' | 'strip'
  category?: MotivationalQuote['category']
}

export const MotivationalQuoteCard: React.FC<MotivationalQuoteCardProps> = ({
  variant = 'hero',
}) => {
  const [quote, setQuote] = useState<MotivationalQuote>(() => getDailyQuote())
  const [isRotating, setIsRotating] = useState(false)
  const [copied, setCopied] = useState(false)

  const handleShuffle = () => {
    playMicroClick()
    setIsRotating(true)
    setTimeout(() => {
      let next = getRandomQuote()
      // Ensure we get a different quote
      if (next.id === quote.id) {
        next = getRandomQuote()
      }
      setQuote(next)
      setIsRotating(false)
    }, 180)
  }

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(`"${quote.quote}" — ${quote.author}${quote.context ? ` (${quote.context})` : ''}`)
      playMicroClick()
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (e) {
      console.warn('Could not copy to clipboard', e)
    }
  }

  const getCategoryIcon = (cat: MotivationalQuote['category']) => {
    switch (cat) {
      case 'strength':
        return <Dumbbell size={13} style={{ color: 'var(--accent-primary)' }} />
      case 'discipline':
        return <Flame size={13} style={{ color: 'var(--accent-amber)' }} />
      case 'resilience':
        return <Heart size={13} style={{ color: 'var(--accent-emerald)' }} />
      case 'greatness':
        return <Award size={13} style={{ color: 'var(--accent-amber)' }} />
      default:
        return <Compass size={13} style={{ color: 'var(--accent-primary)' }} />
    }
  }

  if (variant === 'strip') {
    return (
      <div
        style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-card)',
          borderLeft: '4px solid var(--accent-primary)',
          borderRadius: 'var(--radius-sm)',
          padding: '0.75rem 1rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '1rem',
          flexWrap: 'wrap',
          boxShadow: 'none',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flex: '1 1 300px' }}>
          <div
            style={{
              width: '28px',
              height: '28px',
              borderRadius: '50%',
              background: 'color-mix(in srgb, var(--accent-primary) 15%, transparent)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            <Sparkles size={14} style={{ color: 'var(--accent-primary)' }} />
          </div>
          <div>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-main)', fontWeight: 600, fontStyle: 'italic' }}>
              "{quote.quote}"
            </span>
            <span style={{ fontSize: '0.75rem', color: 'var(--accent-primary)', marginLeft: '0.5rem', fontWeight: 700 }}>
              — {quote.author}
            </span>
          </div>
        </div>

        <button
          type="button"
          className="btn btn-ghost btn-sm"
          onClick={handleShuffle}
          title="Shuffle motivational quote"
          aria-label="New motivational boost"
          style={{ padding: '0.35rem 0.6rem', fontSize: '0.75rem' }}
        >
          <RefreshCw size={13} className={isRotating ? 'spinner' : ''} />
          <span>Morale Boost</span>
        </button>
      </div>
    )
  }

  return (
    <div
      className="card"
      style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-card)',
        borderLeft: '4px solid var(--accent-primary)',
        boxShadow: 'none',
        padding: '1.4rem 1.6rem',
        position: 'relative',
        overflow: 'hidden',
        transition: 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
      }}
    >
      {/* Background Decorative Large Quote Mark */}
      <div
        style={{
          position: 'absolute',
          right: '1.25rem',
          bottom: '-0.75rem',
          fontSize: '7rem',
          fontFamily: 'Georgia, serif',
          color: 'rgba(255, 255, 255, 0.03)',
          lineHeight: 1,
          pointerEvents: 'none',
          userSelect: 'none',
        }}
      >
        "
      </div>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.85rem', flexWrap: 'wrap', gap: '0.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <span
            className="badge"
            style={{
              background: 'color-mix(in srgb, var(--accent-primary) 12%, transparent)',
              color: 'var(--accent-primary)',
              border: '1px solid var(--accent-primary-glow)',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.35rem',
              fontSize: '0.6875rem',
              letterSpacing: '0.06em',
            }}
          >
            {getCategoryIcon(quote.category)}
            MORALE BOOST • {quote.category.toUpperCase()}
          </span>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
            Daily Inspiration
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={handleCopy}
            title="Copy quote"
            aria-label="Copy motivational quote"
            style={{ padding: '0.35rem 0.6rem', fontSize: '0.75rem' }}
          >
            {copied ? <Check size={14} style={{ color: 'var(--accent-emerald)' }} /> : <Copy size={14} />}
            <span>{copied ? 'Copied!' : 'Copy'}</span>
          </button>

          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={handleShuffle}
            title="Shuffle quote"
            aria-label="Get another motivational quote"
            style={{ padding: '0.35rem 0.75rem', fontSize: '0.75rem', display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}
          >
            <RefreshCw size={13} className={isRotating ? 'spinner' : ''} />
            <span>New Boost</span>
          </button>
        </div>
      </div>

      <div
        style={{
          opacity: isRotating ? 0.4 : 1,
          transform: isRotating ? 'scale(0.99)' : 'scale(1)',
          transition: 'all 0.2s ease',
        }}
      >
        <p
          style={{
            fontSize: '1.15rem',
            fontWeight: 600,
            color: 'var(--text-main)',
            lineHeight: 1.6,
            fontStyle: 'italic',
            letterSpacing: '-0.01em',
            marginBottom: '0.75rem',
          }}
        >
          "{quote.quote}"
        </p>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          <strong style={{ color: 'var(--accent-primary)', fontSize: '0.875rem' }}>
            — {quote.author}
          </strong>
          {quote.context && (
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              • {quote.context}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
