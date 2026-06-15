<script setup lang="ts">
import { reactive } from 'vue'
import type { TripFormData } from '../types/trip'

const emit = defineEmits<{
  submit: [data: TripFormData]
}>()

const form = reactive<TripFormData>({
  destination: '',
  startDate: '',
  days: 3,
  travelStyle: 'balanced',
  budgetLevel: 'midrange',
  interests: [],
})

const interestOptions = [
  '历史古迹', '自然风光', '美食探索', '购物',
  '博物馆', '户外运动', '亲子', '夜生活', '摄影',
]

const loading = defineModel<boolean>('loading', { default: false })

function handleSubmit() {
  if (!form.destination || !form.startDate) return
  emit('submit', { ...form })
}
</script>

<template>
  <a-card title="✈️ 规划你的旅行" style="max-width: 700px; margin: 0 auto">
    <a-form layout="vertical" @finish="handleSubmit">
      <a-form-item label="目的地城市" required>
        <a-input
          v-model:value="form.destination"
          placeholder="例如：北京、上海、成都"
          size="large"
        />
      </a-form-item>

      <a-row :gutter="16">
        <a-col :span="12">
          <a-form-item label="出发日期" required>
            <a-date-picker
              v-model:value="form.startDate"
              style="width: 100%"
              size="large"
              :disabled-date="(d: any) => d && d.isBefore(new Date(), 'day')"
            />
          </a-form-item>
        </a-col>
        <a-col :span="12">
          <a-form-item label="旅行天数">
            <a-input-number
              v-model:value="form.days"
              :min="1"
              :max="30"
              style="width: 100%"
              size="large"
            />
          </a-form-item>
        </a-col>
      </a-row>

      <a-row :gutter="16">
        <a-col :span="12">
          <a-form-item label="旅行风格">
            <a-select v-model:value="form.travelStyle" size="large">
              <a-select-option value="relaxed">轻松休闲</a-select-option>
              <a-select-option value="balanced">适中平衡</a-select-option>
              <a-select-option value="intensive">紧凑打卡</a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
        <a-col :span="12">
          <a-form-item label="预算水平">
            <a-select v-model:value="form.budgetLevel" size="large">
              <a-select-option value="budget">经济实惠</a-select-option>
              <a-select-option value="midrange">中等舒适</a-select-option>
              <a-select-option value="luxury">高端奢华</a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
      </a-row>

      <a-form-item label="兴趣爱好">
        <a-checkbox-group v-model:value="form.interests">
          <a-checkbox v-for="opt in interestOptions" :key="opt" :value="opt">
            {{ opt }}
          </a-checkbox>
        </a-checkbox-group>
      </a-form-item>

      <a-form-item>
        <a-button
          type="primary"
          html-type="submit"
          size="large"
          :loading="loading"
          block
        >
          {{ loading ? '正在生成旅行计划...' : '🚀 生成旅行计划' }}
        </a-button>
      </a-form-item>
    </a-form>
  </a-card>
</template>
