import request from './request'

// 认证
export const login = (data: any) => request.post('/auth/login', data)
export const refresh = (data: any) => request.post('/auth/refresh', data)
export const changePassword = (data: any) => request.post('/auth/change-password', data)

// 学生
export const getStudents = (params: any) => request.get('/students', { params })
export const getStudent = (id: number) => request.get(`/students/${id}`)
export const createStudent = (data: any) => request.post('/students', data)
export const updateStudent = (id: number, data: any) => request.put(`/students/${id}`, data)
export const deleteStudent = (id: number) => request.delete(`/students/${id}`)
export const addFamily = (id: number, data: any) => request.post(`/students/${id}/family`, data)
export const importStudents = (formData: FormData) => request.post('/students/import', formData)
export const exportStudents = (params: any) =>
  request.get('/students/export', { params, responseType: 'blob' })

// 班级组织
export const getClasses = () => request.get('/classes')
export const createClass = (data: any) => request.post('/classes', data)
export const getCadres = () => request.get('/cadres')
export const createCadre = (data: any) => request.post('/cadres', data)
export const getDormRooms = () => request.get('/dorm/rooms')
export const createDormRoom = (data: any) => request.post('/dorm/rooms', data)
export const getDormAssignments = () => request.get('/dorm/assignments')
export const createDormAssignment = (data: any) => request.post('/dorm/assignments', data)
export const getSeatPlan = () => request.get('/seat-plan')
export const saveSeatPlan = (data: any) => request.post('/seat-plan', data)
export const getDuty = (params?: any) => request.get('/duty-schedule', { params })
export const createDuty = (data: any) => request.post('/duty-schedule', data)

// 考勤（已删除）
// 成绩
export const getCourses = (params: any) => request.get('/courses', { params })
export const createCourse = (data: any) => request.post('/courses', data)
export const getScores = (params: any) => request.get('/scores', { params })
export const updateScore = (id: number, data: any) => request.put(`/scores/${id}`, data)
export const importScores = (formData: FormData) => request.post('/scores/import', formData)
export const exportScores = (params: any) =>
  request.get('/scores/export', { params, responseType: 'blob' })

// 综合素质评价
export const getQuality = (params: any) => request.get('/quality', { params })
export const evaluateQuality = (data: any) => request.post('/quality/evaluate', data)
export const manualQuality = (data: any) => request.post('/quality/manual', data)
export const deleteQuality = (studentId: number, semester: string) =>
  request.delete(`/quality/${studentId}`, { params: { semester } })
export const exportQuality = (params: any) =>
  request.get('/quality/export', { params, responseType: 'blob' })

// 荣誉
export const getAwards = (params: any) => request.get('/awards', { params })
export const createAward = (data: any) => request.post('/awards', data)
export const getCertificates = (params: any) => request.get('/certificates', { params })
export const createCertificate = (data: any) => request.post('/certificates', data)

// 看板
export const getOverview = () => request.get('/dashboard/overview')
export const getQualityDistribution = () => request.get('/dashboard/quality-distribution')
export const getHonorTop = () => request.get('/dashboard/honor-top')

// 系统
export const getAccount = () => request.get('/account')
export const updateAccount = (data: any) => request.put('/account', data)
export const getSemesters = () => request.get('/semesters')
export const getAuditLogs = (params: any) => request.get('/audit-logs', { params })
export const getBackups = () => request.get('/backups')
export const createBackup = () => request.post('/backup')
export const clearData = () => request.post('/data/clear')

// 上传
export const uploadFile = (formData: FormData) => request.post('/upload', formData)

// 教学安排（课程表 / 实训 / 校历）
export const getScheduleSettings = (params: any) => request.get('/schedule/settings', { params })
export const getScheduleSetting = (params: any) => request.get('/schedule/setting', { params })
export const saveScheduleSetting = (data: any) => request.post('/schedule/setting', data)
export const getScheduleEntries = (settingId: number) => request.get('/schedule/entries', { params: { setting_id: settingId } })
export const saveScheduleEntry = (data: any) => request.post('/schedule/entry', data)
export const deleteScheduleEntry = (id: number) => request.delete(`/schedule/entry/${id}`)
export const getCalendarEvents = (params: any) => request.get('/calendar/events', { params })
export const saveCalendarEvent = (data: any) => request.post('/calendar/event', data)
export const deleteCalendarEvent = (id: number) => request.delete(`/calendar/event/${id}`)
export const importSchedule = (formData: FormData, params: any) => request.post('/schedule/import', formData, { params })
export const downloadScheduleTemplate = () => request.get('/schedule/import-template', { responseType: 'blob' })
export const importCalendarImage = (formData: FormData, params: any) => request.post('/calendar/import-image', formData, { params, timeout: 120000 })
