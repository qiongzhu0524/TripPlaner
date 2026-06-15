import { createApp } from 'vue'
import App from './App.vue'
import router from './router'

// Ant Design Vue 组件库
import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'

const app = createApp(App)
app.use(router)
app.use(Antd)
app.mount('#app')
