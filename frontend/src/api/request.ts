import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
})

request.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

request.interceptors.response.use(
  (response) => {
    // 文件流直接返回
    if (response.config.responseType === 'blob') {
      return response
    }
    const data = response.data
    if (data.code === 0) {
      return data
    }
    if (data.code === 401) {
      localStorage.removeItem('access_token')
      router.push('/login')
    }
    ElMessage.error(data.message || '请求失败')
    return Promise.reject(new Error(data.message))
  },
  (error) => {
    const status = error.response?.status
    const message = error.response?.data?.message
    if (status === 401) {
      localStorage.removeItem('access_token')
      router.push('/login')
    }
    ElMessage.error(message || error.message || '网络错误')
    return Promise.reject(error)
  }
)

export default request
