import { useRef, useState } from 'react'
import { getBatchStatus, uploadCsv, BatchStatusResponse } from '../services/api'

interface Props {
  onImportComplete: (result: BatchStatusResponse) => void
}

export function CsvUploader({ onImportComplete }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [error, setError] = useState<string | null>(null)
  const [status, setStatus] = useState<string | null>(null)
  const [batchStatus, setBatchStatus] = useState<BatchStatusResponse | null>(null)

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return

    if (!file.name.toLowerCase().endsWith('.csv') && file.type !== 'text/csv') {
      setError('Please select a CSV file.')
      return
    }

    setError(null)
    setStatus('processing')
    setBatchStatus(null)

    try {
      const { batch_id } = await uploadCsv(file)

      // Poll until completed or failed
      const poll = async () => {
        const result = await getBatchStatus(batch_id)
        setBatchStatus(result)
        if (result.status === 'completed' || result.status === 'failed') {
          setStatus(result.status)
          onImportComplete(result)
        } else {
          setTimeout(poll, 2000)
        }
      }
      await poll()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Upload failed.'
      setError(msg)
      setStatus(null)
    }
  }

  return (
    <div className="csv-uploader">
      <input
        ref={inputRef}
        type="file"
        accept=".csv,text/csv"
        data-testid="csv-file-input"
        style={{ display: 'none' }}
        onChange={handleFileChange}
      />
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={status === 'processing'}
      >
        {status === 'processing' ? 'Uploading…' : 'Upload CSV'}
      </button>

      {error && <p className="csv-uploader__error">{error}</p>}

      {status === 'processing' && (
        <p className="csv-uploader__status">Processing…</p>
      )}

      {batchStatus?.status === 'completed' && (
        <div className="csv-uploader__report">
          <p>Import complete: {batchStatus.imported_rows} rows imported, {batchStatus.skipped_rows} skipped.</p>
        </div>
      )}
    </div>
  )
}
