"use client";

import React, { useState } from 'react';
import { MTOItem, ItemCategory } from '@/types';
import styles from './MtoTable.module.css';

interface MtoTableProps {
  items: MTOItem[];
}

export default function MtoTable({ items }: MtoTableProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");

  if (!items || items.length === 0) {
    return <div className={styles.empty}>No items found in this MTO.</div>;
  }

  // Get semantic category color tokens defined in globals.css
  const getCategoryColorVar = (category: ItemCategory) => {
    switch (category) {
      case ItemCategory.PIPE: return 'var(--color-cat-pipe)';
      case ItemCategory.FITTING: return 'var(--color-cat-fitting)';
      case ItemCategory.FLANGE: return 'var(--color-cat-flange)';
      case ItemCategory.VALVE: return 'var(--color-cat-valve)';
      case ItemCategory.GASKET: return 'var(--color-cat-gasket)';
      case ItemCategory.BOLT: return 'var(--color-cat-bolt)';
      case ItemCategory.SUPPORT: return 'var(--color-cat-support)';
      case ItemCategory.WELD: return 'var(--color-cat-weld)';
      default: return 'var(--color-secondary-500)';
    }
  };

  // Render color-coded confidence metrics tags
  const renderConfidenceBadge = (confidence?: number | null) => {
    if (confidence === undefined || confidence === null) return '-';
    
    const pct = Math.round(confidence * 100);
    let statusClass = styles.confHigh;
    
    if (confidence < 0.60) {
      statusClass = styles.confLow;
    } else if (confidence < 0.85) {
      statusClass = styles.confMed;
    }

    return (
      <span className={`${styles.confidenceBadge} ${statusClass}`} title={`Confidence rating: ${pct}%`}>
        {pct}%
      </span>
    );
  };

  // List of active categories in the result set for display filters
  const availableCategories = ["ALL", ...Object.values(ItemCategory).filter(cat => 
    items.some(item => item.category === cat)
  )];

  // Apply filters to dataset
  const filteredItems = items.filter(item => {
    const matchesCategory = selectedCategory === "ALL" || item.category === selectedCategory;
    const matchesSearch = 
      item.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (item.material_spec || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
      (item.size_nps || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.category.toLowerCase().includes(searchTerm.toLowerCase());
    
    return matchesCategory && matchesSearch;
  });

  return (
    <div className={styles.container}>
      
      {/* Filtering and Search Controls Toolbar */}
      <div className={styles.filterContainer}>
        {/* Search Input bar */}
        <div className={styles.searchInputWrapper}>
          <svg className={styles.searchIcon} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
          <input
            type="search"
            placeholder="Search descriptions, specs..."
            className={styles.searchInput}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            aria-label="Search material take-off items"
          />
        </div>

        {/* Category Pills Bar */}
        <div className={styles.categoryBar} role="tablist" aria-label="Filter items by category">
          {availableCategories.map((category) => (
            <button
              key={category}
              className={`${styles.filterChip} ${selectedCategory === category ? styles.filterChipActive : ""}`}
              onClick={() => setSelectedCategory(category)}
              role="tab"
              aria-selected={selectedCategory === category}
            >
              {category}
            </button>
          ))}
        </div>
      </div>

      {/* Structured Material Table List */}
      <div className={styles.tableWrapper}>
        {filteredItems.length === 0 ? (
          <div className={styles.empty} style={{ border: 'none' }}>
            No items match your search filters.
          </div>
        ) : (
          <table className={styles.table}>
            <thead>
              <tr>
                <th scope="col" style={{ width: '60px' }}>Mark</th>
                <th scope="col">Category</th>
                <th scope="col">Description</th>
                <th scope="col">Size (NPS)</th>
                <th scope="col">Sch/Rating</th>
                <th scope="col">Material Spec</th>
                <th scope="col">End Type</th>
                <th scope="col">Qty</th>
                <th scope="col">Unit</th>
                <th scope="col">Length</th>
                <th scope="col">Confidence</th>
                <th scope="col">Remarks</th>
              </tr>
            </thead>
            <tbody>
              {filteredItems.map((item, idx) => {
                const color = getCategoryColorVar(item.category);
                return (
                  <tr key={idx}>
                    <td className={styles.number} style={{ color: 'var(--color-secondary-500)', fontSize: '0.8rem' }}>
                      {item.item_no}
                    </td>
                    <td>
                      <span 
                        className={styles.badge} 
                        style={{ 
                          backgroundColor: `${color}15`, 
                          color: color, 
                          border: `1px solid ${color}30` 
                        }}
                      >
                        {item.category}
                      </span>
                    </td>
                    <td className={styles.desc}>{item.description}</td>
                    <td className={styles.number}>{item.size_nps}</td>
                    <td>{item.schedule_rating || '-'}</td>
                    <td>{item.material_spec || '-'}</td>
                    <td style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-secondary-500)' }}>
                      {item.end_type || '-'}
                    </td>
                    <td className={styles.number} style={{ color: '#ffffff' }}>
                      {item.quantity}
                    </td>
                    <td>{item.unit}</td>
                    <td className={styles.number}>
                      {item.length_m ? `${item.length_m.toFixed(2)} m` : '-'}
                    </td>
                    <td>{renderConfidenceBadge(item.confidence)}</td>
                    <td className={styles.remarks}>{item.remarks || '-'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

    </div>
  );
}
