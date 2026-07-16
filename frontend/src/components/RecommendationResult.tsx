import type { RecommendationResponse } from '../services/api'

const CONFIDENCE_LABEL: Record<string, string> = {
  high: 'High Confidence',
  medium: 'Medium Confidence',
  low: 'Low Confidence',
}

function formatEur(value: number): string {
  return value.toLocaleString('de-DE', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}

interface Props {
  result: RecommendationResponse
}

export function RecommendationResult({ result }: Props) {
  return (
    <div className="recommendation-result">
      <div className="recommendation-result__price">
        <h2>Recommended Price</h2>
        <p className="recommendation-result__price-value">
          €{formatEur(result.recommended_price_eur)}/month
        </p>
        <p className="recommendation-result__range">
          Confidence range: €{formatEur(result.confidence_range.low)} – €
          {formatEur(result.confidence_range.high)}
        </p>
        <span className={`badge badge--${result.confidence_level}`}>
          {CONFIDENCE_LABEL[result.confidence_level]}
        </span>
      </div>

      <div className="recommendation-result__stats">
        <p>Based on <strong>{result.comparable_count}</strong> comparable listings</p>
        <p>Percentile rank: <strong>{result.percentile_rank.toFixed(1)}th</strong></p>
      </div>

      {result.data_freshness.is_stale && (
        <p className="recommendation-result__stale-warning">
          ⚠ Data is stale — results may not reflect current market conditions
        </p>
      )}

      <div className="recommendation-result__explanation">
        <h3>Market Analysis</h3>
        {result.explanation_available && result.explanation ? (
          <p>{result.explanation}</p>
        ) : (
          <p className="explanation-unavailable">
            Explanation unavailable — AI service is temporarily offline
          </p>
        )}
      </div>

      <div className="recommendation-result__factors">
        <h3>Key Factors</h3>
        <ul>
          {result.factors.map((factor) => (
            <li key={factor.name}>
              <strong>{factor.name}</strong>: {factor.description}{' '}
              <span className="factor-value">({factor.value})</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
