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
export const getDuty = () => request.get('/duty-schedule')
export const createDuty = (data: any) => request.post('/duty-schedule', data)

// 考勤
export const batchAttendance = (data: any) => request.post('/attendance/batch', data)
export const getAttendance = (params: any) => request.get('/attendance', { params })
export const getAttendanceSummary = (params: any) => request.get('/attendance/summary', { params })
export const exportAttendance = (params: any) =>
  request.get('/attendance/export', { params, responseType: 'blob' })

// 请假
export const createLeave = (data: any) => request.post('/leaves', data)
export const getLeaves = (params: any) => request.get('/leaves', { params })
export const updateLeave = (id: number, data: any) => request.put(`/leaves/${id}`, data)
export const exportLeaves = () => request.get('/leaves/export', { responseType: 'blob' })

// 查寝
export const batchDormCheck = (data: any) => request.post('/dorm-check/batch', data)
export const getDormCheck = (params: any) => request.get('/dorm-check', { params })
export const exportDormCheck = () => request.get('/dorm-check/export', { responseType: 'blob' })

// 纪律
export const createDiscipline = (data: any) => request.post('/discipline', data)
export const getDiscipline = (params: any) => request.get('/discipline', { params })
export const exportDiscipline = () => request.get('/discipline/export', { responseType: 'blob' })

// 成绩
export const getCourses = (params: any) => request.get('/courses', { params })
export const createCourse = (data: any) => request.post('/courses', data)
export const getScores = (params: any) => request.get('/scores', { params })
export const updateScore = (id: number, data: any) => request.put(`/scores/${id}`, data)
export const importScores = (formData: FormData) => request.post('/scores/import', formData)
export const exportScores = (params: any) =>
  request.get('/scores/export', { params, responseType: 'blob' })

// 预警/补考/荣誉
export const getAlerts = (params: any) => request.get('/alerts', { params })
export const exportAlerts = (params: any) =>
  request.get('/alerts/export', { params, responseType: 'blob' })
export const getMakeup = (params: any) => request.get('/makeup', { params })
export const createMakeup = (data: any) => request.post('/makeup', data)
export const updateMakeup = (id: number, data: any) => request.put(`/makeup/${id}`, data)
export const getAwards = (params: any) => request.get('/awards', { params })
export const createAward = (data: any) => request.post('/awards', data)
export const getCertificates = (params: any) => request.get('/certificates', { params })
export const createCertificate = (data: any) => request.post('/certificates', data)

// 看板
export const getOverview = () => request.get('/dashboard/overview')
export const getAttendanceTrend = (params: any) =>
  request.get('/dashboard/attendance-trend', { params })
export const getScoreDistribution = (params: any) =>
  request.get('/dashboard/score-distribution', { params })
export const getRankings = () => request.get('/dashboard/rankings')

// 系统
export const getAccount = () => request.get('/account')
export const updateAccount = (data: any) => request.put('/account', data)
export const getAuditLogs = (params: any) => request.get('/audit-logs', { params })
export const getBackups = () => request.get('/backups')
export const createBackup = () => request.post('/backup')

// 上传
export const uploadFile = (formData: FormData) => request.post('/upload', formData)
