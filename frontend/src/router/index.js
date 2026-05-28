import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    component: () => import('../components/Layout.vue'),
    children: [
      {
        path: '',
        name: 'KanbanList',
        component: () => import('../views/KanbanList.vue'),
      },
      {
        path: 'kanban/:id',
        name: 'KanbanView',
        component: () => import('../views/KanbanView.vue'),
      },
      {
        path: 'approvals',
        name: 'ApprovalPanel',
        component: () => import('../views/ApprovalPanel.vue'),
      },
      {
        path: 'schedules',
        name: 'ScheduleManager',
        component: () => import('../views/ScheduleManager.vue'),
      },
      {
        path: 'logs',
        name: 'LogManager',
        component: () => import('../views/LogManager.vue'),
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('../views/SettingsView.vue'),
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
