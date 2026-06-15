<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

<template>
  <a-layout style="min-height: 100vh">
    <a-layout-header style="background: #001529; padding: 0 24px; display: flex; align-items: center">
      <h1 style="color: white; margin: 0; font-size: 20px">
        🌍 TripPlaner AI — 智能旅行助手
      </h1>
    </a-layout-header>
    <a-layout-content style="padding: 24px">
      <RouterView />
    </a-layout-content>
    <a-layout-footer style="text-align: center">
      TripPlaner AI ©2026 — Built with Vue 3 + FastAPI + ReAct Agent
    </a-layout-footer>
  </a-layout>
</template>
