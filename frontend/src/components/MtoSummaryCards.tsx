"use client";

import React, { useState } from 'react';
import { MTOSummary } from '@/types';
import styles from './MtoSummaryCards.module.css';

interface MtoSummaryCardsProps {
  summary: MTOSummary;
}

export default function MtoSummaryCards({ summary }: MtoSummaryCardsProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  if (!summary) return null;

  const cards = [
    { 
      label: 'Total Pipe', 
      value: `${summary.total_pipe_length_m.toFixed(1)} m`, 
      color: 'var(--color-cat-pipe)', 
      bg: 'rgba(56, 189, 248, 0.1)', 
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 8h18" />
          <path d="M3 16h18" />
          <path d="M3 8v8" />
          <path d="M21 8v8" />
        </svg>
      )
    },
    { 
      label: 'Fittings', 
      value: summary.fittings, 
      color: 'var(--color-cat-fitting)', 
      bg: 'rgba(52, 211, 153, 0.1)', 
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M8 3v5a4 4 0 0 0 4 4h9" />
          <path d="M4 3v9a8 8 0 0 0 8 8h9" />
        </svg>
      )
    },
    { 
      label: 'Flanges', 
      value: summary.flanges, 
      color: 'var(--color-cat-flange)', 
      bg: 'rgba(251, 191, 36, 0.1)', 
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="5" y="3" width="4" height="18" rx="1" />
          <rect x="15" y="3" width="4" height="18" rx="1" />
          <path d="M9 12h6" />
        </svg>
      )
    },
    { 
      label: 'Valves', 
      value: summary.valves, 
      color: 'var(--color-cat-valve)', 
      bg: 'rgba(248, 113, 113, 0.1)', 
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <polygon points="3 6 3 18 21 6 21 18 3 6" />
          <circle cx="12" cy="12" r="2.5" fill="currentColor" />
        </svg>
      )
    },
    { 
      label: 'Gaskets', 
      value: summary.gaskets, 
      color: 'var(--color-cat-gasket)', 
      bg: 'rgba(167, 139, 250, 0.1)', 
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
          <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2.2" />
          <circle cx="12" cy="12" r="5" stroke="currentColor" strokeWidth="1.8" />
        </svg>
      )
    },
    { 
      label: 'Bolt Sets', 
      value: summary.bolt_sets, 
      color: 'var(--color-cat-bolt)', 
      bg: 'rgba(244, 114, 182, 0.1)', 
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="10" width="14" height="4" rx="1" />
          <path d="M17 12h4" />
          <circle cx="7" cy="12" r="1" fill="currentColor" />
          <circle cx="13" cy="12" r="1" fill="currentColor" />
        </svg>
      )
    },
    { 
      label: 'Supports', 
      value: summary.supports, 
      color: 'var(--color-cat-support)', 
      bg: 'rgba(34, 211, 238, 0.1)', 
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M4 3h16" />
          <path d="M12 3v12" />
          <path d="M8 15h8v2H8z" />
          <path d="M6 21h12" />
        </svg>
      )
    },
    { 
      label: 'Field Welds', 
      value: summary.field_welds, 
      color: 'var(--color-cat-weld)', 
      bg: 'rgba(45, 212, 191, 0.1)', 
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
        </svg>
      )
    },
  ];

  return (
    <div className={styles.grid}>
      {cards.map((card, idx) => {
        const isHovered = hoveredIndex === idx;
        return (
          <div 
            key={idx} 
            className={styles.card}
            onMouseEnter={() => setHoveredIndex(idx)}
            onMouseLeave={() => setHoveredIndex(null)}
            style={{
              borderColor: isHovered ? card.color : undefined,
              boxShadow: isHovered ? `0 0 20px ${card.color}25` : undefined
            }}
          >
            <div className={styles.cardHeader}>
              <div 
                className={styles.iconWrapper} 
                style={{ 
                  backgroundColor: card.bg, 
                  color: card.color,
                  borderColor: `${card.color}35`
                }}
              >
                {card.icon}
              </div>
            </div>
            <div className={styles.info}>
              <div className={styles.value}>{card.value}</div>
              <div className={styles.label}>{card.label}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
