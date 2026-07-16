import { useQuery } from '@tanstack/react-query'
import { getListingsStatus, ListingsStatusResponse } from '../services/api'

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const hours = Math.floor(diff / 3_600_000)
  if (hours < 1) return 'less than an hour ago'
  if (hours === 1) return '1 hour ago'
  if (hours < 24) return `${hours} hours ago`
  const days = Math.floor(hours / 24)
  return `${days} day${days > 1 ? 's' : ''} ago`
}

interface Props {
  status: ListingsStatusResponse
  isStale?: boolean
}

export function DataFreshnessBar({ status, isStale }: Props) {
  if (!status.last_upload_at || status.total_listings === 0) {
    return (
      <div className="freshness-bar freshness-bar--empty">
        No data uploaded yet. Upload a CSV to get started.
      </div>
    )
  }

  return (
    <div className={`freshness-bar${isStale ? ' freshness-bar--stale' : ''}`}>
      <span>
        <strong>{status.total_listings.toLocaleString('de-DE')}</strong> listings · Last
        upload: {timeAgo(status.last_upload_at)}
      </span>
      {isStale && (
        <span className="freshness-bar__warning">
          ⚠ Data is stale — please upload a new CSV
        </span>
      )}
    </div>
  )
}

export function DataFreshnessBarConnected() {
  const { data } = useQuery({
    queryKey: ['listings-status'],
    queryFn: getListingsStatus,
    refetchInterval: 30_000,
  })

  if (!data) return null

  const isStale =
    data.last_upload_at
      ? Date.now() - new Date(data.last_upload_at).getTime() > 48 * 3_600_000
      : false

  return <DataFreshnessBar status={data} isStale={isStale} />
}
