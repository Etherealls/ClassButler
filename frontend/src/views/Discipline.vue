<template>
  <div class="page-container">
    <div class="toolbar">
      <el-select v-model="filterStudent" placeholder="按学生筛选" clearable filterable style="width: 200px" @change="load">
        <el-option v-for="s in students" :key="s.id" :label="`${s.name}（${s.student_no}）`" :value="s.id" />
      </el-select>
      <el-select v-model="filterCategory" placeholder="违纪类型" clearable style="width: 140px" @change="load">
        <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
      </el-select>
      <div class="spacer"></div>
      <el-button @click="handleExport">导出纪律台账</el-button>
      <el-button type="primary" @click="openDialog">登记纪律</el-button>
    </div>

    <el-table :data="list" border stripe v-loading="loading">
      <el-table-column prop="student_no" label="学号" width="100" />
      <el-table-column prop="student_name" label="姓名" width="100" />
      <el-table-column prop="category" label="违纪类型" width="110" />
      <el-table-column prop="occur_time" label="时间" width="160" />
      <el-table-column prop="location" label="地点" width="120" />
      <el-table-column prop="fact" label="事实描述" show-overflow-tooltip />
      <el-table-column prop="result" label="处理结果" show-overflow-tooltip />
    </el-table>
    <el-pagination class="pagination" :current-page="page" :page-size="size" :total="total" layout="total, prev, pager, next" @current-change="(p: number) => { page = p; load() }" />

    <el-dialog v-model="dialogVisible" title="登记纪律" width="560px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="学生" required>
          <el-select v-model="form.student_id" filterable style="width: 100%">
            <el-option v-for="s in students" :key="s.id" :label="`${s.name}（${s.student_no}）`" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="违纪类型" required>
          <el-select v-model="form.category" style="width: 100%">
            <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="时间" required>
          <el-date-picker v-model="form.occur_time" type="datetime" value-format="YYYY-MM-DD HH:mm" style="width: 100%" />
        </el-form-item>
        <el-form-item label="地点"><el-input v-model="form.location" /></el-form-item>
        <el-form-item label="事实描述" required><el-input v-model="form.fact" type="textarea" /></el-form-item>
        <el-form-item label="处理结果"><el-input v-model="form.result" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" @click="handleSave">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getStudents, getDiscipline, createDiscipline, exportDiscipline } from '@/api'

const categories = ['课堂违纪', '抽烟', '打架', '迟到再犯', '其他']
const list = ref<any[]>([])
const students = ref<any[]>([])
const loading = ref(false)
const filterStudent = ref<any>(null)
const filterCategory = ref('')
const page = ref(1)
const size = ref(20)
const total = ref(0)
const dialogVisible = ref(false)
const form = reactive<any>({})

const load = async () => {
  loading.value = true
  try {
    const res: any = await getDiscipline({ student_id: filterStudent.value || undefined, category: filterCategory.value || undefined, page: page.value, size: size.value })
    list.value = res.data
    total.value = res.total
  } finally {
    loading.value = false
  }
}

const openDialog = () => { Object.keys(form).forEach((k) => delete form[k]); dialogVisible.value = true }

const handleSave = async () => {
  if (!form.student_id || !form.category || !form.occur_time || !form.fact) {
    ElMessage.warning('请填写完整'); return
  }
  await createDiscipline(form)
  ElMessage.success('已登记')
  dialogVisible.value = false
  load()
}

const handleExport = async () => {
  const res: any = await exportDiscipline()
  const url = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = url; a.download = 'discipline.xlsx'; a.click(); URL.revokeObjectURL(url)
}

onMounted(async () => {
  load()
  const res: any = await getStudents({ page: 1, size: 200 })
  students.value = res.data
})
</script>

<style scoped>
.pagination { margin-top: 16px; justify-content: flex-end; }
</style>
