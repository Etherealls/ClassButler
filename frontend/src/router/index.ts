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
      { path: 'attendance', name: 'attendance', component: () => import('@/views/Attendance.vue'), meta: { title: '考勤管理' } },
      { path: 'leaves', name: 'leaves', component: () => import('@/views/Leaves.vue'), meta: { title: '请假登记' } },
      { path: 'dorm-check', name: 'dorm-check', component: () => import('@/views/DormCheck.vue'), meta: { title: '查寝管理' } },
      { path: 'discipline', name: 'discipline', component: () => import('@/views/Discipline.vue'), meta: { title: '纪律记录' } },
      { path: 'scores', name: 'scores', component: () => import('@/views/Scores.vue'), meta: { title: '成绩管理' } },
      { path: 'alerts', name: 'alerts', component: () => import('@/views/Alerts.vue'), meta: { title: '学业预警' } },
      { path: 'makeup', name: 'makeup', component: () => import('@/views/Makeup.vue'), meta: { title: '补考重修' } },
      { path: 'honors', name: 'honors', component: () => import('@/views/Honors.vue'), meta: { title: '荣誉证书' } },
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
  if (to.path !== '/login' && !token) {
    next('/login')
  } else if (to.path === '/login' && token) {
    next('/')
  } else {
    next()
  }
})

export default router
