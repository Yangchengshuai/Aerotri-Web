import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Home',
    component: () => import('./views/HomeView.vue'),
  },
  {
    path: '/block/:id',
    name: 'BlockDetail',
    component: () => import('./views/BlockDetailView.vue'),
  },
  {
    path: '/compare',
    name: 'Compare',
    component: () => import('./views/CompareView.vue'),
  },
  {
    path: '/compare/recon/:blockId',
    name: 'ReconCompare',
    component: () => import('./views/ReconCompareView.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
