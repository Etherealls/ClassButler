<template>
  <div class="page-container">
    <div class="toolbar">
      <el-select v-model="semester" placeholder="选择学期" style="width: 220px" @change="load">
        <el-option v-for="s in semesters" :key="s.value" :label="s.label" :value="s.value" :disabled="!s.editable && !s.readonly" />
      </el-select>
      <el-button type="primary" @click="load">查询</el-button>
      <div class="spacer"></div>
      <el-button v-if="!isReadonly" @click="openCourseDialog">添加课程</el-button>
      <el-upload v-if="!isReadonly" :show-file-list="false" :before-upload="handleImport" accept=".xlsx">
        <el-button>批量导入成绩</el-button>
      </el-upload>
      <el-button @click="handleExport">导出成绩表</el-button>
    </div>

    <el-alert v-if="isReadonly" type="warning" :closable="false" style="margin-bottom: 16px">
      当前为历史学期，数据仅可查看，不可添加课程、导入或修改成绩。
    </el-alert>

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
        <el-form-item label="学期" required>
          <el-select v-model="courseForm.semester" style="width: 100%">
            <el-option v-for="s in semesters" :key="s.value" :label="s.label" :value="s.value" :disabled="!s.editable" />
          </el-select>
        </el-form-item>
        <el-form-item label="学分"><el-input-number v-model="courseForm.credit" :min="0" :max="20" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="courseDialog = false">取消</el-button><el-button type="primary" @click="saveCourse">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getScores, createCourse, importScores, exportScores, getSemesters } from '@/api'

const semester = ref('')
const semesters = ref<any[]>([])
const students = ref<any[]>([])
const courses = ref<any[]>([])
const stats = ref<any>({})
const loading = ref(false)
const courseDialog = ref(false)
const courseForm = reactive<any>({ credit: 1 })

// 当前选中学期是否为历史学期（只读）
const isReadonly = computed(() => {
  const s = semesters.value.find((x) => x.value === semester.value)
  return !!s?.readonly
})

const load = async () => {
  if (!semester.value) { ElMessage.warning('请选择学期'); return }
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
  if (!semester.value) { ElMessage.warning('请先选择学期'); return false }
  if (isReadonly.value) { ElMessage.warning('历史学期不可导入成绩'); return false }
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
  if (!semester.value) { ElMessage.warning('请选择学期'); return }
  const res: any = await exportScores({ semester: semester.value })
  const url = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = url; a.download = `scores_${semester.value}.xlsx`; a.click(); URL.revokeObjectURL(url)
}

onMounted(async () => {
  // 获取学期列表
  const res: any = await getSemesters()
  semesters.value = res.data.semesters
  const cur = res.data.editable_semester || res.data.current_semester
  if (cur) {
    semester.value = cur
    load()
  } else {
    ElMessage.warning('请先在账号设置中填写开始担任班主任的学期')
  }
})
</script>
