import { useState } from 'react';
import type { FormEvent } from 'react';
import type { DecodeResult } from '../types';
import { decode } from '../api/client';

interface PasteBoxProps {
  onResult: (result: DecodeResult) => void;
}

const SAMPLE_TEXT = `NOTICE OF TERMINATION

Address: 14 Oakwood Grove, Dublin 9
Tenancy commenced on 3 April 2023.

Dear Tenant,

The landlord intends to sell the property within the next 3 months and is
therefore terminating your tenancy. You are required to vacate the property
within 14 days of this notice.

Date of this notice: 21 June 2026`;

export default function PasteBox({ onResult }: PasteBoxProps) {
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!text.trim() || loading) return;
    setLoading(true);
    setError(null);
    try {
      const result = await decode(text);
      onResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-white rounded-2xl border border-stone-200 shadow-sm p-5 sm:p-7"
    >
      <label
        htmlFor="doc-text"
        className="mb-3 block text-sm font-semibold text-stone-700"
      >
        Paste your letter, notice, or bill
      </label>

      <textarea
        id="doc-text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Paste the full text of the tenancy notice, insurance letter, medical bill, or government letter here..."
        rows={12}
        className="w-full resize-y rounded-xl border border-stone-300 bg-stone-50 p-4 text-sm leading-relaxed text-stone-800 shadow-inner focus:border-indigo-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-100"
      />

      <div className="mt-4 flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between">
        <button
          type="button"
          onClick={() => setText(SAMPLE_TEXT)}
          className="text-xs font-medium text-indigo-600 hover:text-indigo-800"
        >
          Try sample notice
        </button>

        <button
          type="submit"
          disabled={loading || !text.trim()}
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-stone-300"
        >
          {loading && (
            <span
              aria-hidden
              className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white"
            />
          )}
          {loading ? 'Checking against the rules...' : 'Decode this document'}
        </button>
      </div>

      {error && (
        <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}
    </form>
  );
}
