import { defineStore } from 'pinia'
import { login as apiLogin } from '@/api'

export const useUserStore = defineStore('user', {
  state: () => ({
    accessToken: localStorage.getItem('access_token') || '',
    refreshToken: localStorage.getItem('refresh_token') || '',
    username: localStorage.getItem('username') || '',
    classId: Number(localStorage.getItem('class_id') || 0) || null,
    startSemester: localStorage.getItem('start_semester') || '',
    mustChangePwd: false,
  }),
  getters: {
    isLoggedIn: (state) => !!state.accessToken,
  },
  actions: {
    async login(username: string, password: string) {
      const res: any = await apiLogin({ username, password })
      const d = res.data
      this.accessToken = d.access_token
      this.refreshToken = d.refresh_token
      this.username = d.username
      this.classId = d.class_id
      this.mustChangePwd = d.must_change_pwd
      this.startSemester = d.start_semester || ''
      localStorage.setItem('access_token', d.access_token)
      localStorage.setItem('refresh_token', d.refresh_token)
      localStorage.setItem('username', d.username)
      if (d.class_id) localStorage.setItem('class_id', String(d.class_id))
      if (d.start_semester) localStorage.setItem('start_semester', d.start_semester)
      else localStorage.removeItem('start_semester')
      return d
    },
    updateStartSemester(sem: string) {
      this.startSemester = sem
      if (sem) localStorage.setItem('start_semester', sem)
      else localStorage.removeItem('start_semester')
    },
    logout() {
      this.accessToken = ''
      this.refreshToken = ''
      this.username = ''
      this.classId = null
      this.startSemester = ''
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('username')
      localStorage.removeItem('class_id')
      localStorage.removeItem('start_semester')
    },
  },
})
