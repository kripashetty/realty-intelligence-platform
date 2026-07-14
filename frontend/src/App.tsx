import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RecommendationPage } from './pages/RecommendationPage'

const queryClient = new QueryClient()

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <RecommendationPage />
    </QueryClientProvider>
  )
}

export default App
