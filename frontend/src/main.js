
import { createApp } from 'vue'
import App from './App.vue'
import i18n from './i18n' // Import i18n instance
import './assets/main.css'

const app = createApp(App)
app.use(i18n) // Use i18n
app.mount('#app')
