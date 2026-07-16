import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  getListingsStatus,
  getRecommendation,
  ApartmentRequest,
  RecommendationResponse,
  BatchStatusResponse,
} from '../services/api'
import { ApartmentForm } from '../components/ApartmentForm'
import { CsvUploader } from '../components/CsvUploader'
import { DataFreshnessBar } from '../components/DataFreshnessBar'
import { RecommendationResult } from '../components/RecommendationResult'

export function RecommendationPage() {
  const [result, setResult] = useState<RecommendationResponse | null>(null)

  const { data: statusData, refetch: refetchStatus } = useQuery({
    queryKey: ['listings-status'],
    queryFn: getListingsStatus,
    refetchInterval: 30_000,
  })

  const isStale =
    statusData?.last_upload_at
      ? Date.now() - new Date(statusData.last_upload_at).getTime() > 48 * 3_600_000
      : false

  const recommendMutation = useMutation({
    mutationFn: (req: ApartmentRequest) => getRecommendation(req),
    onSuccess: (data) => setResult(data),
  })

  function handleImportComplete(_batch: BatchStatusResponse) {
    refetchStatus()
  }

  const hasData = (statusData?.total_listings ?? 0) > 0

  return (
    <main className="recommendation-page">
      <h1>Berlin Rental Price Advisor</h1>

      {statusData && (
        <DataFreshnessBar status={statusData} isStale={isStale} />
      )}

      <section className="recommendation-page__uploader">
        <h2>Upload Market Data</h2>
        <CsvUploader onImportComplete={handleImportComplete} />
      </section>

      {!hasData && (
        <p className="recommendation-page__no-data">
          Upload a Fredy CSV export to enable pricing recommendations.
        </p>
      )}

      {hasData && (
        <section className="recommendation-page__form">
          <h2>Get Pricing Recommendation</h2>
          <ApartmentForm
            onSubmit={(data) => recommendMutation.mutate(data)}
            isLoading={recommendMutation.isPending}
          />
          {recommendMutation.isError && (
            <p className="recommendation-page__error">
              {(recommendMutation.error as { message?: string })?.message ??
                'Failed to get recommendation.'}
            </p>
          )}
        </section>
      )}

      {result && (
        <section className="recommendation-page__result">
          <RecommendationResult result={result} />
        </section>
      )}
    </main>
  )
}
