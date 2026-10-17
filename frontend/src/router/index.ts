import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/login', name: 'login', component: () => import('@/views/Login.vue') },
  {
    path: '/',
    component: () => import('@/layout/MainLayout.vue'),
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', name: 'dashboard', component: () => import('@/views/Dashboard.vue'), meta: { title: '数据看板' } },
      { path: 'students', name: 'students', component: () => import('@/views/Students.vue'), meta: { title: '学生档案' } },
      { path: 'organization', name: 'organization', component: () => import('@/views/Organization.vue'), meta: { title: '班级组织' } },
      { path: 'scores', name: 'scores', component: () => import('@/views/Scores.vue'), meta: { title: '成绩管理' } },
      { path: 'quality', name: 'quality', component: () => import('@/views/Quality.vue'), meta: { title: '综合素质评价' } },
      { path: 'honors', name: 'honors', component: () => import('@/views/Honors.vue'), meta: { title: '荣誉证书' } },
      { path: 'schedule', name: 'schedule', component: () => import('@/views/Schedule.vue'), meta: { title: '教学安排' } },
      { path: 'account', name: 'account', component: () => import('@/views/Account.vue'), meta: { title: '账号设置' } },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('access_token')
  const startSemester = localStorage.getItem('start_semester')
  if (to.path !== '/login' && !token) {
    next('/login')
  } else if (to.path === '/login' && token) {
    next('/')
  } else if (
    token &&
    !startSemester &&
    to.path !== '/account' &&
    to.path !== '/login'
  ) {
    // 已登录但未设置开始学期，强制跳转到账号页选择
    next('/account')
  } else {
    next()
  }
})

export default router
