import { createRouter, createWebHistory } from 'vue-router'

const TABS = ['active', 'alerts', 'lists', 'pipeline', 'duplicates', 'history'] as const

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/active' },
    ...TABS.map(tab => ({ path: `/${tab}`, name: tab, component: { template: '' } })),
    { path: '/register/:token', name: 'register', component: { template: '' } },
  ],
})

export default router
