<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import TripForm from '../components/TripForm.vue'
import { planTrip } from '../services/api'
import type { TripFormData } from '../types/trip'

const router = useRouter()
const loading = ref(false)

async function handleSubmit(data: TripFormData) {
  loading.value = true
  try {
    const result = await planTrip({
      user_id: 'default',
      destination: data.destination,
      start_date: data.startDate,
      days: data.days,
      travel_style: data.travelStyle,
      budget_level: data.budgetLevel,
      interests: data.interests.length > 0 ? data.interests : undefined,
    })
    message.success('旅行计划生成成功！')
    router.push({
      name: 'result',
      params: { tripId: result.trip_id },
      state: { plan: result },
    })
  } catch (e: any) {
    message.error(`生成失败: ${e.response?.data?.detail || e.message}`)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div style="max-width: 800px; margin: 0 auto; padding: 24px 0">
    <div style="text-align: center; margin-bottom: 32px">
      <h2>🌍 智能旅行规划</h2>
      <p style="color: #666">
        基于 AI Agent + 高德地图 MCP 工具，为你生成个性化的旅行行程
      </p>
    </div>

    <TripForm v-model:loading="loading" @submit="handleSubmit" />
  </div>
</template>
