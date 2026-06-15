<script setup lang="ts">
/**
 * 高德地图 JS API 集成组件。
 *
 * 需要在 index.html 中通过 <script> 标签加载高德 JS API Key：
 *   <script src="https://webapi.amap.com/maps?v=2.0&key=YOUR_KEY"></script>
 *
 * 或者，该组件可以通过动态脚本加载来增强。
 * 目前，它是一个占位组件，配置 API Key 后可启用。
 */

import { ref, onMounted, watch } from 'vue'

interface POIMarker {
  name: string
  lat: number
  lng: number
}

const props = defineProps<{
  markers?: POIMarker[]
  center?: { lat: number; lng: number }
  zoom?: number
}>()

const mapContainer = ref<HTMLDivElement>()
let mapInstance: any = null

onMounted(() => {
  if (!mapContainer.value) return

  // 检查高德地图 API 是否已加载
  if (typeof window !== 'undefined' && (window as any).AMap) {
    initMap()
  } else {
    // 占位：提示需要配置高德地图 API Key
    console.log('Amap JS API not loaded — add API key to index.html')
  }
})

function initMap() {
  const AMap = (window as any).AMap
  const center = props.center || { lat: 39.9042, lng: 116.4074 } // 默认：北京

  mapInstance = new AMap.Map(mapContainer.value!, {
    zoom: props.zoom || 12,
    center: [center.lng, center.lat],
  })

  // Add markers
  if (props.markers) {
    props.markers.forEach((m) => {
      new AMap.Marker({
        position: [m.lng, m.lat],
        title: m.name,
        map: mapInstance,
      })
    })
  }
}

watch(
  () => props.markers,
  (newMarkers) => {
    if (mapInstance && newMarkers) {
      const AMap = (window as any).AMap
      mapInstance.clearMap()
      newMarkers.forEach((m) => {
        new AMap.Marker({
          position: [m.lng, m.lat],
          title: m.name,
          map: mapInstance,
        })
      })
    }
  },
)
</script>

<template>
  <div
    ref="mapContainer"
    style="width: 100%; height: 400px; border-radius: 8px; background: #f0f0f0"
  >
    <div
      v-if="!mapInstance"
      style="display: flex; align-items: center; justify-content: center; height: 100%; color: #999"
    >
      <span>🗺️ 地图组件 — 配置高德 JS API Key 后启用</span>
    </div>
  </div>
</template>
