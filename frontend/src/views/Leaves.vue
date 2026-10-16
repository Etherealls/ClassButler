<template>
  <div class="page-container">
    <div class="toolbar">
      <el-select v-model="filterType" placeholder="类型" clearable style="width: 120px" @change="load">
        <el-option label="事假" value="PERSONAL" />
        <el-option label="病假" value="SICK" />
        <el-option label="公假" value="PUBLIC" />
      </el-select>
      <el-select v-model="filterStatus" placeholder="状态" clearable style="width: 120px" @change="load">
        <el-option label="请假中" value="LEAVING" />
        <el-option label="已结束" value="FINISHED" />
      </el-select>
      <div class="spacer"></div>
      <el-button @click="handleExport">导出请假台账</el-button>
      <el-button type="primary" @click="openDialog">登记请假</el-button>
    </div>

    <el-table :data="list" border stripe v-loading="loading">
      <el-table-column prop="student_no" label="学号" width="100" />
      <el-table-column prop="student_name" label="姓名" width="100" />
      <el-table-column prop="leave_type_label" label="类型" width="80" />
      <el-table-column prop="start_time" label="开始时间" width="160" />
      <el-table-column prop="end_time" label="结束时间" width="160" />
      <el-table-column prop="duration_hours" label="时长(时)" width="90" />
      <el-table-column prop="destination" label="去向" width="100" />
      <el-table-column prop="reason" label="事由" show-overflow-tooltip />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'LEAVING' ? (row.overdue ? 'danger' : 'warning') : 'info'" size="small">
            {{ row.status_label }}{{ row.overdue ? '（逾期）' : '' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button v-if="row.status === 'LEAVING'" link type="primary" @click="finishLeave(row)">销假</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination class="pagination" :current-page="page" :page-size="size" :total="total" layout="total, prev, pager, next" @current-change="(p: number) => { page = p; load() }" />

    <el-dialog v-model="dialogVisible" title="登记请假" width="560px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="学生" required>
          <el-select v-model="form.student_id" filterable style="width: 100%">
            <el-option v-for="s in students" :key="s.id" :label="`${s.name}（${s.student_no}）`" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="类型" required>
          <el-radio-group v-model="form.leave_type">
            <el-radio label="PERSONAL">事假</el-radio>
            <el-radio label="SICK">病假</el-radio>
            <el-radio label="PUBLIC">公假</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="开始时间" required>
          <el-date-picker v-model="form.start_time" type="datetime" value-format="YYYY-MM-DD HH:mm" style="width: 100%" />
        </el-form-item>
        <el-form-item label="结束时间" required>
          <el-date-picker v-model="form.end_time" type="datetime" value-format="YYYY-MM-DD HH:mm" style="width: 100%" />
        </el-form-item>
        <el-form-item label="时长(小时)"><el-input-number v-model="form.duration_hours" :min="0" :max="720" /></el-form-item>
        <el-form-item label="去向"><el-input v-model="form.destination" /></el-form-item>
        <el-form-item label="事由" required><el-input v-model="form.reason" type="textarea" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" @click="handleSave">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getStudents, getLeaves, createLeave, updateLeave, exportLeaves } from '@/api'

const list = ref<any[]>([])
const students = ref<any[]>([])
const loading = ref(false)
const filterType = ref('')
const filterStatus = ref('')
const page = ref(1)
const size = ref(20)
const total = ref(0)
const dialogVisible = ref(false)
const form = reactive<any>({ leave_type: 'PERSONAL' })

const load = async () => {
  loading.value = true
  try {
    const res: any = await getLeaves({ leave_type: filterType.value || undefined, status: filterStatus.value || undefined, page: page.value, size: size.value })
    list.value = res.data
    total.value = res.total
  } finally {
    loading.value = false
  }
}

const openDialog = () => {
  Object.keys(form).forEach((k) => delete form[k])
  form.leave_type = 'PERSONAL'
  dialogVisible.value = true
}

const handleSave = async () => {
  if (!form.student_id || !form.start_time || !form.end_time || !form.reason) {
    ElMessage.warning('请填写完整'); return
  }
  await createLeave(form)
  ElMessage.success('请假已登记')
  dialogVisible.value = false
  load()
}

const finishLeave = async (row: any) => {
  await updateLeave(row.id, { status: 'FINISHED' })
  ElMessage.success('已销假')
  load()
}

const handleExport = async () => {
  const res: any = await exportLeaves()
  const url = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = url; a.download = 'leaves.xlsx'; a.click(); URL.revokeObjectURL(url)
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
