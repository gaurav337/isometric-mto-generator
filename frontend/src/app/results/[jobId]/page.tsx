"use client";

import React, { useEffect, useState } from 'react';
import { getMTOResult, getMtoCsvUrl } from '@/lib/api';
import { MTOResponse, JobStatus } from '@/types';
import MtoTable from '@/components/MtoTable';
import MtoSummaryCards from '@/components/MtoSummaryCards';
import DrawingMeta from '@/components/DrawingMeta';
import styles from './page.module.css';
import Link from 'next/link';

export default function ResultsPage({ params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = React.use(params);
  const [data, setData] = useState<MTOResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [zoom, setZoom] = useState<number>(1);

  useEffect(() => {
    let mounted = true;

    const fetchData = async () => {
      try {
        console.log(`[Frontend Debug] Fetching MTO result for jobId: ${jobId}`);
        const result = await getMTOResult(jobId);
        console.log(`[Frontend Debug] Received response for jobId: ${jobId}. Status: ${result.status}, Source: ${result.source}`, result);
        if (mounted) {
          setData(result);
          if (result.status === JobStatus.PENDING || result.status === JobStatus.RUNNING) {
            // Re-poll if not complete
            setTimeout(fetchData, 2000);
          } else {
            setLoading(false);
          }
        }
      } catch (err: unknown) {
        console.error(`[Frontend Debug] Error fetching MTO result for jobId: ${jobId}:`, err);
        if (mounted) {
          setError(err instanceof Error ? err.message : 'An error occurred while fetching results.');
          setLoading(false);
        }
      }
    };

    fetchData();

    return () => {
      mounted = false;
    };
  }, [jobId]);

  // Zoom controls helper functions
  const zoomIn = () => setZoom(prev => Math.min(prev + 0.2, 3));
  const zoomOut = () => setZoom(prev => Math.max(prev - 0.2, 0.5));
  const resetZoom = () => setZoom(1);

  const isStillProcessing = loading || (data && (data.status === JobStatus.PENDING || data.status === JobStatus.RUNNING));

  if (isStillProcessing) {
    const isPending = data?.status === JobStatus.PENDING;
    const isRunning = data?.status === JobStatus.RUNNING || !data;

    return (
      <div className={styles.loadingContainer} role="status">
        <div className={styles.spinner}></div>
        <h2 className={styles.loadingText}>Processing Drawing</h2>
        <p className={styles.loadingSubtext}>Our Vision AI pipeline is analyzing the isometric drawing blueprint.</p>
        
        {/* Step-by-step extraction workflow timeline */}
        <div className={styles.progressTracker}>
          <div className={`${styles.progressItem} ${styles.progressItemDone}`}>
            <span className={styles.statusIndicator}>✔ File received & uploaded</span>
            <span>OK</span>
          </div>
          
          <div className={`${styles.progressItem} ${isRunning ? styles.progressItemActive : isPending ? styles.progressItemPending : styles.progressItemDone}`}>
            <span className={styles.statusIndicator}>
              {isRunning ? (
                <>
                  <span style={{ width: '8px', height: '8px', backgroundColor: 'var(--color-primary-500)', borderRadius: '50%', display: 'inline-block', animation: 'pulse 1.5s infinite', marginRight: '6px' }} />
                  Running Vision LLM extraction...
                </>
              ) : isPending ? (
                "⏳ Queueing Vision LLM extraction..."
              ) : (
                "✔ Vision LLM extraction complete"
              )}
            </span>
            <span>{isRunning ? "Running" : isPending ? "Queueing" : "OK"}</span>
          </div>

          <div className={`${styles.progressItem} ${styles.progressItemPending}`}>
            <span>⏳ ASME validation check</span>
            <span>Pending</span>
          </div>
          <div className={`${styles.progressItem} ${styles.progressItemPending}`}>
            <span>⏳ Joint consumables calculations</span>
            <span>Pending</span>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.errorContainer} role="alert">
        <div className={styles.errorIcon}>⚠</div>
        <h2 className={styles.errorTitle}>Extraction Failed</h2>
        <p className={styles.errorMessage}>{error}</p>
        <Link href="/" className="btn btn--primary">Try Another Drawing</Link>
      </div>
    );
  }

  if (data?.status === JobStatus.FAILED) {
    return (
      <div className={styles.errorContainer} role="alert">
        <div className={styles.errorIcon}>⚠</div>
        <h2 className={styles.errorTitle}>Job Process Failed</h2>
        <p className={styles.errorMessage}>{data.error_message || 'The AI pipeline encountered an error processing this file.'}</p>
        <Link href="/" className="btn btn--primary">Try Another Drawing</Link>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      {/* Workspace Sub-header */}
      <div className={styles.header}>
        <div className={styles.titleSection}>
          <h2 className={styles.title}>Workspace Dashboard</h2>
          <div className={styles.badges}>
            <span className={styles.statusBadge} aria-label="Status: Completed">
              <span style={{ width: '6px', height: '6px', backgroundColor: '#10b981', borderRadius: '50%', display: 'inline-block' }} />
              Extracted
            </span>
            <span className={styles.sourceBadge}>Pipeline: {data?.source === 'nvidia' ? 'NVIDIA Llama' : data?.source === 'gemini' ? 'Google Gemini' : data?.source === 'openrouter' ? 'OpenRouter' : 'Mock Fallback'}</span>
          </div>
        </div>
        <div className={styles.actions}>
          <Link href="/" className="btn btn--secondary">Upload New</Link>
          <a href={getMtoCsvUrl(jobId)} className="btn btn--primary" download aria-label="Download CSV report">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
            Download CSV
          </a>
        </div>
      </div>

      {/* Side-by-Side Split Workspace Layout */}
      <div className={styles.mainLayout}>
        
        {/* Left Side: Sticky Drawing Viewport with Zoom Controls */}
        <section className={styles.imageColumn} aria-label="Drawing blueprint viewport">
          <div className={styles.viewerToolbar}>
            <span className={styles.toolbarTitle}>Isometric drawing preview</span>
            <div className={styles.toolbarActions}>
              <button onClick={zoomOut} className={styles.toolbarBtn} title="Zoom Out" aria-label="Zoom Out">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><line x1="5" y1="12" x2="19" y2="12"></line></svg>
              </button>
              <button onClick={resetZoom} className={styles.toolbarBtn} title="Reset Zoom" aria-label="Reset Zoom">
                <span style={{ fontSize: '10px', fontWeight: 'bold' }}>1:1</span>
              </button>
              <button onClick={zoomIn} className={styles.toolbarBtn} title="Zoom In" aria-label="Zoom In">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
              </button>
            </div>
          </div>
          <div className={styles.imagePreviewWrapper}>
            {data?.image_b64 ? (
              /* eslint-disable-next-line @next/next/no-img-element */
              <img 
                src={data.image_b64} 
                alt="Piping Isometric Drawing Blueprint Sheet" 
                className={styles.imagePreview} 
                style={{ transform: `scale(${zoom})`, transformOrigin: 'center center' }}
              />
            ) : (
              <div className={styles.emptyImage}>
                No preview image available
              </div>
            )}
          </div>
        </section>

        {/* Right Side: Tabulated engineering records */}
        <div className={styles.dataColumn}>
          {data?.drawing_meta && (
            <section aria-label="Title block details">
              <DrawingMeta meta={data.drawing_meta} />
            </section>
          )}
          
          {data?.summary && (
            <section aria-label="Isometric summary statistics">
              <MtoSummaryCards summary={data.summary} />
            </section>
          )}
          
          <section className={styles.tableSection} aria-label="Material Take-Off listings">
            <h3 className={styles.sectionTitle}>Material Take-Off List</h3>
            <MtoTable items={data?.items || []} />
          </section>
        </div>

      </div>
    </div>
  );
}
