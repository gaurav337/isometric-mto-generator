import UploadZone from "@/components/UploadZone";
import styles from "./page.module.css";

export default function Home() {
  return (
    <div className={styles.homeContainer}>
      {/* Hero Header Section */}
      <section className={styles.hero}>
        <h2 className={styles.heroTitle}>
          Piping Material Take-Offs, Instantly.
        </h2>
        <p className={styles.heroSubtitle}>
          Upload your piping isometric drawing (PNG, JPG, or PDF) and let our Vision AI instantly extract structured BOM items, metadata, and derived consumables.
        </p>
      </section>

      {/* Interactive File Dropzone wrapper */}
      <div className={styles.uploadWrapper}>
        <UploadZone />
      </div>

      {/* Application Key Capabilities Grid */}
      <section className={styles.featuresGrid}>
        <div className={styles.featureCard}>
          <div className={styles.featureIconWrapper}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M15 12h-5" />
              <path d="M15 8h-5" />
              <path d="M19 17V5a2 2 0 0 0-2-2H4" />
              <path d="M8 21h12a2 2 0 0 0 2-2v-1a1 1 0 0 0-1-1H11a1 1 0 0 0-1 1v1a2 2 0 0 1-2 2v0a2 2 0 0 1-2-2v-9" />
              <circle cx="8" cy="6" r="3" />
            </svg>
          </div>
          <div className={styles.featureContent}>
            <h3>Vision AI Extractions</h3>
            <p>Processes complex drawings via Google Gemini and NVIDIA Llama NIMs to identify linear runs and component symbols.</p>
          </div>
        </div>

        <div className={styles.featureCard}>
          <div className={styles.featureIconWrapper}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <path d="m10 15 5-5" />
              <path d="m15 15-5-5" />
            </svg>
          </div>
          <div className={styles.featureContent}>
            <h3>Joint Consumables</h3>
            <p>Calculates gasket counts and stud bolt quantities automatically from the mating flange schedule, rating, and size dimensions.</p>
          </div>
        </div>

        <div className={styles.featureCard}>
          <div className={styles.featureIconWrapper}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
          </div>
          <div className={styles.featureContent}>
            <h3>ASME Specifications</h3>
            <p>Standardizes metadata entries against ASME B16.9 (fittings), B16.5 (flanges), and B16.34 (valves) codes.</p>
          </div>
        </div>

        <div className={styles.featureCard}>
          <div className={styles.featureIconWrapper}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
          </div>
          <div className={styles.featureContent}>
            <h3>Standard CSV Outputs</h3>
            <p>Download the extracted take-offs directly as structured CSV files formatted for instant engineering database loading.</p>
          </div>
        </div>
      </section>
    </div>
  );
}
