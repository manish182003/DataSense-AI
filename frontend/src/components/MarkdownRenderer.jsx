import React from 'react';
import { FileText, Sparkles, ChevronRight, Quote } from 'lucide-react';

export default function MarkdownRenderer({ content }) {
  if (!content) return null;

  const renderFormattedInline = (text) => {
    if (!text) return null;

    // Handle HTML <br> or <br/> tags inside text/cells cleanly
    if (typeof text === 'string' && /<br\s*\/?>/i.test(text)) {
      const subSegments = text.split(/<br\s*\/?>/i);
      return subSegments.map((sub, sIdx) => (
        <React.Fragment key={sIdx}>
          {sIdx > 0 && <br />}
          {renderFormattedInline(sub)}
        </React.Fragment>
      ));
    }

    // Split on:
    // 1. Inline Code: `code`
    // 2. Bold: **text**
    // 3. Italic: *text* or _text_
    // 4. Citations: [Source: ...] or [Doc: ...]
    const tokenRegex = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*|_[^_]+_|\[Source:.*?\]|\[Doc:.*?\])/g;
    const parts = text.split(tokenRegex);

    return parts.map((part, idx) => {
      if (!part) return null;

      // Inline code `code`
      if (part.startsWith('`') && part.endsWith('`') && part.length >= 2) {
        const codeContent = part.slice(1, -1);
        return <code key={idx} className="inline-code-chip">{codeContent}</code>;
      }

      // Citations
      if (part.startsWith('[Source:') || part.startsWith('[Doc:')) {
        const cleanCitation = part.replace(/^\[(Source|Doc):\s*/, '').replace(/\]$/, '');
        return (
          <span key={idx} className="inline-citation-tag">
            <FileText className="icon-tiny text-purple" /> {cleanCitation}
          </span>
        );
      }

      // Bold **text**
      if (part.startsWith('**') && part.endsWith('**') && part.length >= 4) {
        const boldText = part.slice(2, -2);
        return <strong key={idx} className="text-highlight">{boldText}</strong>;
      }

      // Italic *text* or _text_
      if ((part.startsWith('*') && part.endsWith('*') && part.length >= 2) ||
          (part.startsWith('_') && part.endsWith('_') && part.length >= 2)) {
        const italicText = part.slice(1, -1);
        return <em key={idx} className="text-italic">{italicText}</em>;
      }

      return part;
    });
  };

  // Block parser to group lines into tables, lists, headers, divider lines, and paragraphs
  const rawLines = content.split('\n');
  const blocks = [];
  let currentTable = null;

  rawLines.forEach((line) => {
    const trimmed = line.trim();
    if (!trimmed) {
      currentTable = null;
      return;
    }

    // 1. Horizontal divider rules (---, ***, ___)
    if (/^[\s]*[-*_]{3,}[\s]*$/.test(trimmed)) {
      currentTable = null;
      blocks.push({ type: 'hr' });
      return;
    }

    // 2. Check if line is part of a pipe markdown table (| col1 | col2 |)
    const isPipeTable = (trimmed.startsWith('|') && trimmed.endsWith('|')) || (trimmed.split('|').length >= 3);
    const isTabTable = trimmed.includes('\t') && trimmed.split('\t').length >= 2;

    if (isPipeTable) {
      // Ignore divider rows like |---|---|
      if (/^\|?[\s\-:]+(\|[\s\-:]+)+\|?$/.test(trimmed)) {
        return;
      }

      const cells = trimmed
        .split('|')
        .filter((cell, idx, arr) => (idx > 0 && idx < arr.length - 1) || cell.trim().length > 0)
        .map((cell) => cell.trim());

      if (cells.length >= 2) {
        if (!currentTable || currentTable.mode !== 'pipe') {
          currentTable = { type: 'table', mode: 'pipe', headers: cells, rows: [] };
          blocks.push(currentTable);
        } else {
          currentTable.rows.push(cells);
        }
        return;
      }
    } else if (isTabTable) {
      const cells = trimmed.split('\t').map((c) => c.trim()).filter(Boolean);
      if (cells.length >= 2) {
        if (!currentTable || currentTable.mode !== 'tab') {
          currentTable = { type: 'table', mode: 'tab', headers: cells, rows: [] };
          blocks.push(currentTable);
        } else {
          currentTable.rows.push(cells);
        }
        return;
      }
    }

    currentTable = null;
    blocks.push({ type: 'line', text: trimmed });
  });

  return (
    <div className="markdown-rich-content">
      {blocks.map((block, bIdx) => {
        if (block.type === 'hr') {
          return <hr key={bIdx} className="markdown-hr" />;
        }

        if (block.type === 'table') {
          return (
            <div key={bIdx} className="markdown-table-wrapper margin-y">
              <table className="rendered-markdown-table">
                <thead>
                  <tr>
                    {block.headers.map((h, hIdx) => (
                      <th key={hIdx}>{renderFormattedInline(h)}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {block.rows.map((row, rIdx) => (
                    <tr key={rIdx}>
                      {row.map((cell, cIdx) => (
                        <td key={cIdx}>{renderFormattedInline(cell)}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        }

        const trimmed = block.text;

        // Blockquotes (e.g. > quote)
        if (trimmed.startsWith('>')) {
          const quoteText = trimmed.replace(/^>\s*/, '');
          return (
            <blockquote key={bIdx} className="markdown-quote">
              <Quote className="icon-tiny text-purple quote-icon" />
              <span>{renderFormattedInline(quoteText)}</span>
            </blockquote>
          );
        }

        // Headers (e.g. ### Header or ## Header)
        if (trimmed.startsWith('#')) {
          const level = (trimmed.match(/^#+/) || ['#'])[0].length;
          const headerText = trimmed.replace(/^#+\s*/, '');
          return (
            <h4 key={bIdx} className={`markdown-header header-level-${level}`}>
              <Sparkles className="icon-tiny text-blue" /> {renderFormattedInline(headerText)}
            </h4>
          );
        }

        // Bullet lists (e.g. - item or * item)
        if (trimmed.startsWith('-') || trimmed.startsWith('*')) {
          const bulletText = trimmed.replace(/^[-*]\s*/, '');
          return (
            <div key={bIdx} className="markdown-bullet-row">
              <span className="bullet-icon"><ChevronRight className="icon-tiny text-blue" /></span>
              <span className="bullet-text">{renderFormattedInline(bulletText)}</span>
            </div>
          );
        }

        // Numbered lists (e.g. 1. item)
        const numMatch = trimmed.match(/^(\d+)[\.\)]\s*(.*)/);
        if (numMatch) {
          const num = numMatch[1];
          const numText = numMatch[2];
          return (
            <div key={bIdx} className="markdown-numbered-row">
              <span className="number-pill">{num}</span>
              <span className="numbered-text">{renderFormattedInline(numText)}</span>
            </div>
          );
        }

        // Standard paragraph
        return (
          <p key={bIdx} className="markdown-paragraph">
            {renderFormattedInline(trimmed)}
          </p>
        );
      })}
    </div>
  );
}
