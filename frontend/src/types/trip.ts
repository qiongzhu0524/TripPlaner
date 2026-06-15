/** TripPlaner 前端的 TypeScript 类型定义。 */

export interface TripPlanRequest {
  user_id: string
  destination: string
  start_date: string // YYYY-MM-DD
  days: number
  travel_style?: 'relaxed' | 'balanced' | 'intensive'
  budget_level?: 'budget' | 'midrange' | 'luxury'
  dietary_preferences?: string[]
  interests?: string[]
}

export interface TripPlanResponse {
  trip_id: string
  destination: string
  start_date: string
  end_date: string
  days: number
  content: string
  tool_calls_made: ToolCallRecord[]
  iterations: number
  usage: TokenUsage | null
}

export interface ToolCallRecord {
  tool: string
  args_summary: string
}

export interface TokenUsage {
  input_tokens: number
  output_tokens: number
}

export interface POIItem {
  name: string
  address: string
  lat: number
  lng: number
  category: string
  rating: string
}

export interface POISearchResponse {
  results: POIItem[]
  total: number
}

export interface WeatherForecast {
  date: string
  temperature_high: number
  temperature_low: number
  weather: string
}

export interface WeatherResponse {
  city: string
  forecasts: WeatherForecast[]
}

export interface ChatRequest {
  user_id: string
  session_id: string
  message: string
}

export interface ChatResponse {
  session_id: string
  response: string
  tool_calls: ToolCallRecord[]
}

export interface TripFormData {
  destination: string
  startDate: string
  days: number
  travelStyle: 'relaxed' | 'balanced' | 'intensive'
  budgetLevel: 'budget' | 'midrange' | 'luxury'
  interests: string[]
}
