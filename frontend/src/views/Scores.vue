<template>
  <div class="page-container">
    <div class="toolbar">
      <el-input v-model="semester" placeholder="学期，如 2024-2025-1" style="width: 180px" />
      <el-button type="primary" @click="load">查询</el-button>
      <div class="spacer"></div>
      <el-button @click="openCourseDialog">添加课程</el-button>
      <el-upload :show-file-list="false" :before-upload="handleImport" accept=".xlsx">
        <el-button>批量导入成绩</el-button>
      </el-upload>
      <el-button @click="handleExport">导出成绩表</el-button>
    </div>

    <el-alert v-if="stats.avg" type="success" :closable="false" style="margin-bottom: 16px">
      平均分：{{ stats.avg }}　最高：{{ stats.max }}　最低：{{ stats.min }}　及格率：{{ stats.pass_rate }}%　优秀率：{{ stats.excellent_rate }}%
    </el-alert>

    <el-table :data="students" border stripe v-loading="loading" max-height="600">
      <el-table-column prop="rank" label="排名" width="70" />
      <el-table-column prop="student_no" label="学号" width="100" fixed="left" />
      <el-table-column prop="student_name" label="姓名" width="100" fixed="left" />
      <el-table-column v-for="c in courses" :key="c.id" :label="c.course_name" width="110">
        <template #default="{ row }">
          <span :style="{ color: row.scores[c.id] != null && row.scores[c.id] < 60 ? '#f56c6c' : '#303133' }">
            {{ row.scores[c.id] ?? '—' }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="total" label="总分" width="90" />
      <el-table-column prop="average" label="均分" width="90" />
      <el-table-column prop="fail_count" label="挂科数" width="80" />
    </el-table>

    <el-dialog v-model="courseDialog" title="添加课程" width="420px">
      <el-form :model="courseForm" label-width="90px">
        <el-form-item label="课程名" required><el-input v-model="courseForm.course_name" /></el-form-item>
        <el-form-item label="学期" required><el-input v-model="courseForm.semester" placeholder="如 2024-2025-1" /></el-form-item>
        <el-form-item label="学分"><el-input-number v-model="courseForm.credit" :min="0" :max="20" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="courseDialog = false">取消</el-button><el-button type="primary" @click="saveCourse">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getScores, createCourse, importScores, exportScores } from '@/api'

const semester = ref('')
const students = ref<any[]>([])
const courses = ref<any[]>([])
const stats = ref<any>({})
const loading = ref(false)
const courseDialog = ref(false)
const courseForm = reactive<any>({ credit: 1 })

const load = async () => {
  if (!semester.value) { ElMessage.warning('请输入学期'); return }
  loading.value = true
  try {
    const res: any = await getScores({ semester: semester.value })
    students.value = res.data.students
    courses.value = res.data.courses
    stats.value = res.data.stats
  } finally {
    loading.value = false
  }
}

const openCourseDialog = () => {
  courseForm.course_name = ''
  courseForm.semester = semester.value
  courseForm.credit = 1
  courseDialog.value = true
}

const saveCourse = async () => {
  if (!courseForm.course_name || !courseForm.semester) { ElMessage.warning('请填写完整'); return }
  await createCourse(courseForm)
  ElMessage.success('课程已添加')
  courseDialog.value = false
  load()
}

const handleImport = async (file: File) => {
  if (!semester.value) { ElMessage.warning('请先输入学期'); return false }
  const fd = new FormData()
  fd.append('file', file)
  fd.append('semester', semester.value)
  const res: any = await importScores(fd)
  const { success, errors } = res.data
  if (errors && errors.length) {
    ElMessage.warning(`成功 ${success} 条，失败 ${errors.length} 条`)
  } else {
    ElMessage.success(`导入成功 ${success} 条`)
  }
  load()
  return false
}

const handleExport = async () => {
  if (!semester.value) { ElMessage.warning('请输入学期'); return }
  const res: any = await exportScores({ semester: semester.value })
  const url = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = url; a.download = `scores_${semester.value}.xlsx`; a.click(); URL.revokeObjectURL(url)
}

onMounted(() => {
  // 默认取当前学期
  const now = new Date()
  const y = now.getFullYear()
  const m = now.getMonth() + 1
  const sem = m >= 8 ? `${y}-${y + 1}-1` : `${y - 1}-${y}-2`
  semester.value = sem
  load()
})
</script>
