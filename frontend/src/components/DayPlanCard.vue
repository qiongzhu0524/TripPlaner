<script setup lang="ts">
defineProps<{
  day: number
  date: string
  activities: Array<{
    timeSlot: string
    name: string
    description: string
    location: string
  }>
}>()
</script>

<template>
  <a-card :title="`第 ${day} 天 — ${date}`" style="margin-bottom: 16px">
    <a-timeline>
      <a-timeline-item
        v-for="(act, idx) in activities"
        :key="idx"
        :color="idx === 0 ? 'green' : 'blue'"
      >
        <strong>{{ act.timeSlot }}: {{ act.name }}</strong>
        <br />
        <span style="color: #666">📍 {{ act.location }}</span>
        <br />
        <span>{{ act.description }}</span>
      </a-timeline-item>
    </a-timeline>
  </a-card>
</template>
