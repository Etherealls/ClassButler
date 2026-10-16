<template>
  <div class="page-container">
    <div class="toolbar">
      <el-button type="primary" @click="openDialog">登记补考/重修</el-button>
    </div>
    <el-table :data="list" border stripe v-loading="loading">
      <el-table-column prop="student_no" label="学号" width="100" />
      <el-table-column prop="student_name" label="姓名" width="100" />
      <el-table-column prop="course_name" label="课程" />
      <el-table-column label="阶段" width="120">
        <template #default="{ row }">
          <el-tag :type="stageType(row.stage)" size="small">{{ stageLabel(row.stage) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="exam_time" label="考试时间" width="160" />
      <el-table-column prop="result_score" label="成绩" width="80" />
      <el-table-column prop="note" label="备注" />
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">更新</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="editing ? '更新补考记录' : '登记补考/重修'" width="500px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="学生" required>
          <el-select v-model="form.student_id" filterable style="width: 100%" :disabled="editing">
            <el-option v-for="s in students" :key="s.id" :label="`${s.name}（${s.student_no}）`" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="课程" required>
          <el-select v-model="form.course_id" filterable style="width: 100%" :disabled="editing">
            <el-option v-for="c in courses" :key="c.id" :label="`${c.course_name}（${c.semester}）`" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="阶段">
          <el-select v-model="form.stage" style="width: 100%">
            <el-option label="待补考" value="WAIT_MAKEUP" />
            <el-option label="补考通过" value="MAKEUP_PASSED" />
            <el-option label="补考未过" value="REMAKEUP_FAIL" />
            <el-option label="重修" value="RETAKE" />
          </el-select>
        </el-form-item>
        <el-form-item label="考试时间"><el-date-picker v-model="form.exam_time" type="datetime" value-format="YYYY-MM-DD HH:mm" style="width: 100%" /></el-form-item>
        <el-form-item label="成绩"><el-input-number v-model="form.result_score" :min="0" :max="100" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="form.note" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" @click="handleSave">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getStudents, getCourses, getMakeup, createMakeup, updateMakeup } from '@/api'

const list = ref<any[]>([])
const students = ref<any[]>([])
const courses = ref<any[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const editing = ref(false)
const form = reactive<any>({ stage: 'WAIT_MAKEUP' })

const stageLabel = (s: string) => ({ WAIT_MAKEUP: '待补考', MAKEUP_PASSED: '补考通过', REMAKEUP_FAIL: '补考未过', RETAKE: '重修' } as any)[s] || s
const stageType = (s: string) => ({ WAIT_MAKEUP: 'warning', MAKEUP_PASSED: 'success', REMAKEUP_FAIL: 'danger', RETAKE: 'info' } as any)[s] || 'info'

const load = async () => {
  loading.value = true
  try {
    const res: any = await getMakeup({})
    list.value = res.data
  } finally {
    loading.value = false
  }
}

const openDialog = () => { editing.value = false; Object.keys(form).forEach((k) => delete form[k]); form.stage = 'WAIT_MAKEUP'; dialogVisible.value = true }
const openEdit = (row: any) => { editing.value = true; Object.assign(form, row); dialogVisible.value = true }

const handleSave = async () => {
  if (!form.student_id || !form.course_id) { ElMessage.warning('请选择学生和课程'); return }
  if (editing.value) {
    await updateMakeup(form.id, { stage: form.stage, exam_time: form.exam_time, result_score: form.result_score, note: form.note })
    ElMessage.success('已更新')
  } else {
    await createMakeup(form)
    ElMessage.success('已登记')
  }
  dialogVisible.value = false
  load()
}

onMounted(async () => {
  load()
  const [s, c] = await Promise.all([getStudents({ page: 1, size: 200 }), getCourses({})])
  students.value = (s as any).data
  courses.value = (c as any).data
})
</script>
