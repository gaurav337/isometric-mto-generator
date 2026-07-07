import React from 'react';
import { DrawingMetadata } from '@/types';
import styles from './DrawingMeta.module.css';

interface DrawingMetaProps {
  meta: DrawingMetadata;
}

export default function DrawingMeta({ meta }: DrawingMetaProps) {
  if (!meta) return null;

  return (
    <div className={styles.container}>
      {/* Top Banner Header */}
      <div className={styles.header}>
        <h3 className={styles.title}>
          <svg className={styles.titleIcon} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
            <line x1="16" y1="13" x2="8" y2="13"></line>
            <line x1="16" y1="17" x2="8" y2="17"></line>
            <polyline points="10 9 9 9 8 9"></polyline>
          </svg>
          Drawing Title Block Details
        </h3>
      </div>

      {/* Structured Specification Cards */}
      <div className={styles.sectionsWrapper}>
        
        {/* Section 1: Sheet Identity Metadata */}
        <div className={styles.metaSection}>
          <h4 className={styles.sectionTitle}>
            <svg className={styles.sectionIcon} width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
            Sheet Identification
          </h4>
          <div className={styles.specList}>
            <div className={styles.specRow}>
              <span className={styles.label}>Drawing Number</span>
              <span className={styles.value}>{meta.drawing_no || 'N/A'}</span>
            </div>
            <div className={styles.specRow}>
              <span className={styles.label}>Sheet Revision</span>
              <span className={`${styles.value} ${styles.badgeValue}`}>Rev {meta.revision || '0'}</span>
            </div>
            <div className={styles.specRow}>
              <span className={styles.label}>Piping Line Number</span>
              <span className={styles.value} style={{ color: 'var(--color-primary-500)' }}>{meta.line_number || 'N/A'}</span>
            </div>
          </div>
        </div>

        {/* Section 2: Technical Design Specifications */}
        <div className={styles.metaSection}>
          <h4 className={styles.sectionTitle}>
            <svg className={styles.sectionIcon} width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polygon points="12 2 2 7 12 12 22 7 12 2"></polygon><polyline points="2 17 12 22 22 17"></polyline><polyline points="2 12 12 17 22 12"></polyline></svg>
            Design Specifications
          </h4>
          <div className={styles.specList}>
            <div className={styles.specRow}>
              <span className={styles.label}>Nominal Size (NPS)</span>
              <span className={styles.value}>{meta.nps || 'N/A'}</span>
            </div>
            <div className={styles.specRow}>
              <span className={styles.label}>Material Spec Class</span>
              <span className={styles.value}>{meta.material_class || 'N/A'}</span>
            </div>
            <div className={styles.specRow}>
              <span className={styles.label}>Process Service</span>
              <span className={styles.value}>{meta.service || 'N/A'}</span>
            </div>
            <div className={styles.specRow}>
              <span className={styles.label}>Design Pressure/Temp</span>
              <span className={styles.value} style={{ fontSize: '0.8rem' }}>
                {meta.design_pressure || '-'} / {meta.design_temperature || '-'}
              </span>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
