"use client";

import React, { useState, useRef } from "react";
import { uploadDrawing } from "@/lib/api";
import { useRouter } from "next/navigation";
import styles from "./UploadZone.module.css";

export default function UploadZone() {
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const validateAndUpload = async (file: File) => {
    setError(null);
    const validTypes = ["image/jpeg", "image/png", "application/pdf"];
    if (!validTypes.includes(file.type)) {
      setError("Unsupported file format. Please upload a high-resolution PNG, JPG, or PDF isometric drawing.");
      return;
    }

    if (file.size > 20 * 1024 * 1024) {
      setError("File exceeds the 20MB limit. Please compress your drawing or choose a lower DPI version.");
      return;
    }

    setIsUploading(true);
    try {
      const result = await uploadDrawing(file);
      router.push(`/results/${result.job_id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to upload and process the drawing. Please verify connection and try again.");
      setIsUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndUpload(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      validateAndUpload(e.target.files[0]);
    }
  };

  const onButtonClick = () => {
    inputRef.current?.click();
  };

  return (
    <div className={styles.container}>
      <form
        className={`${styles.dropzone} ${dragActive ? styles.active : ""}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onSubmit={(e) => e.preventDefault()}
        onClick={onButtonClick}
        role="button"
        aria-label="Upload isometric drawing file dropzone"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onButtonClick();
          }
        }}
      >
        <input
          ref={inputRef}
          type="file"
          className={styles.input}
          accept="image/jpeg, image/png, application/pdf"
          onChange={handleChange}
          disabled={isUploading}
          aria-hidden="true"
        />
        
        <div className={styles.content}>
          <div className={styles.iconWrapper}>
            {isUploading ? (
              <svg className={`${styles.icon} animate-spin`} width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" style={{ animation: 'spin 1.5s linear infinite' }}>
                <circle cx="12" cy="12" r="10" />
                <path d="M12 2a10 10 0 0 1 10 10" />
              </svg>
            ) : (
              <svg
                className={styles.icon}
                fill="none"
                stroke="currentColor"
                strokeWidth={2.2}
                viewBox="0 0 24 24"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 13h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            )}
          </div>
          
          <p className={styles.title}>
            {isUploading ? "Uploading Isometric Drawing..." : "Drag & drop Isometric drawing"}
          </p>
          <p className={styles.subtitle}>
            PNG, JPG, or PDF blueprint sheets (Up to 20MB)
          </p>

          <button
            type="button"
            className={styles.button}
            onClick={(e) => {
              e.stopPropagation(); // Avoid double trigger due to parent onClick
              onButtonClick();
            }}
            disabled={isUploading}
            aria-live="polite"
          >
            {isUploading ? (
              <>
                <span style={{ fontSize: '0.9rem' }}>Uploading...</span>
              </>
            ) : (
              "Browse Files"
            )}
          </button>
        </div>
      </form>
      
      {error && (
        <div className={styles.error} role="alert">
          <span className={styles.errorIcon} aria-hidden="true">⚠</span>
          <div>
            <strong style={{ display: 'block', marginBottom: '0.15rem', color: '#f87171' }}>Upload Error</strong>
            <span>{error}</span>
          </div>
        </div>
      )}
    </div>
  );
}
