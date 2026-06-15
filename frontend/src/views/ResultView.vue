<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import type { TripPlanResponse } from '../types/trip'
import DayPlanCard from '../components/DayPlanCard.vue'

const route = useRoute()
const plan = ref<TripPlanResponse | null>(null)
const loading = ref(false)

onMounted(() => {
  const state = history.state as { plan?: TripPlanResponse } | null
  if (state?.plan) {
    plan.value = state.plan
  } else {
    message.warning('行程数据未找到，请重新规划')
  }
})

function formatContent(content: string): string {
  // 将类 Markdown 内容转换为 HTML 友好格式
  return content
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br/>')
}
</script>

<template>
  <div v-if="plan" style="max-width: 900px; margin: 0 auto">
    <a-page-header
      :title="`${plan.destination} — ${plan.days}日游`"
      sub-title="AI 生成的旅行计划"
      @back="() => $router.push('/')"
    />

    <!-- 统计信息 -->
    <a-row :gutter="16" style="margin-bottom: 24px">
      <a-col :span="6">
        <a-statistic title="工具调用" :value="plan.tool_calls_made?.length || 0" suffix="次" />
      </a-col>
      <a-col :span="6">
        <a-statistic title="Agent 迭代" :value="plan.iterations" suffix="轮" />
      </a-col>
      <a-col :span="6">
        <a-statistic
          v-if="plan.usage"
          title="输入Token"
          :value="plan.usage.input_tokens"
        />
      </a-col>
      <a-col :span="6">
        <a-statistic
          v-if="plan.usage"
          title="输出Token"
          :value="plan.usage.output_tokens"
        />
      </a-col>
    </a-row>

    <!-- 工具调用记录 -->
    <a-card title="🔧 工具调用记录" size="small" style="margin-bottom: 24px">
      <a-tag
        v-for="tc in plan.tool_calls_made"
        :key="tc.tool"
        color="blue"
        style="margin: 4px"
      >
        {{ tc.tool }}: {{ tc.args_summary }}
      </a-tag>
      <span v-if="!plan.tool_calls_made?.length" style="color: #999">
        本次未调用工具（Agent 直接回答）
      </span>
    </a-card>

    <!-- 行程详情 -->
    <a-card title="📋 行程详情">
      <div
        style="white-space: pre-wrap; line-height: 1.8"
        v-html="formatContent(plan.content)"
      />
    </a-card>
  </div>

  <a-empty v-else description="无行程数据" />
</template>
