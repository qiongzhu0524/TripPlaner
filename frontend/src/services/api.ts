/** TripPlaner 后端的 API 客户端。 */

import axios from 'axios'
import type {
  TripPlanRequest,
  TripPlanResponse,
  POISearchResponse,
  WeatherResponse,
  ChatRequest,
  ChatResponse,
} from '../types/trip'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000, // LLM 调用超时 2 分钟
  headers: { 'Content-Type': 'application/json' },
})

/** 生成完整的旅行计划。 */
export async function planTrip(req: TripPlanRequest): Promise<TripPlanResponse> {
  const { data } = await api.post<TripPlanResponse>('/trip/plan', req)
  return data
}

/** 搜索兴趣点（POI）。 */
export async function searchPOIs(
  keywords: string,
  city: string,
  limit = 10,
): Promise<POISearchResponse> {
  const { data } = await api.get<POISearchResponse>('/map/poi/search', {
    params: { keywords, city, limit },
  })
  return data
}

/** 查询天气预报。 */
export async function getWeather(city: string): Promise<WeatherResponse> {
  const { data } = await api.get<WeatherResponse>('/map/weather', {
    params: { city },
  })
  return data
}

/** 向 Agent 发送聊天消息。 */
export async function sendChatMessage(req: ChatRequest): Promise<ChatResponse> {
  const { data } = await api.post<ChatResponse>('/chat/message', req)
  return data
}

/** 创建实时聊天的 SSE 流。 */
export function createChatStream(
  userId: string,
  message: string,
  sessionId?: string,
  onEvent?: (eventType: string, data: any) => void,
  onError?: (error: Event) => void,
): EventSource {
  const params = new URLSearchParams({ user_id: userId, message })
  if (sessionId) params.set('session_id', sessionId)

  const es = new EventSource(`/api/chat/message/stream?${params.toString()}`)

  es.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data)
      onEvent?.(payload.type, payload.data)
    } catch {
      // 忽略解析错误
    }
  }

  es.onerror = (event) => {
    onError?.(event)
  }

  return es
}
