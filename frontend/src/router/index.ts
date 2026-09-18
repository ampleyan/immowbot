import { createRouter, createWebHistory } from 'vue-router'

const TABS = ['home', 'active', 'alerts', 'lists', 'pipeline', 'tools'] as const

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/home' },
    ...TABS.map(tab => ({ path: `/${tab}`, name: tab, component: { template: '' } })),
    { path: '/register/:token', name: 'register', component: { template: '' } },
  ],
})

export default router
