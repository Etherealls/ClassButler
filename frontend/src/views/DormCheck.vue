<template>
  <div class="page-container">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="夜查登记" name="check">
        <div class="toolbar">
          <el-date-picker v-model="checkDate" type="date" value-format="YYYY-MM-DD" placeholder="日期" />
          <el-button type="primary" @click="loadCheckStudents">加载住宿学生</el-button>
          <div class="spacer"></div>
          <el-button type="success" @click="submitCheck">保存查寝</el-button>
        </div>
        <el-table :data="checkStudents" border stripe v-loading="loading">
          <el-table-column prop="student_no" label="学号" width="100" />
          <el-table-column prop="name" label="姓名" width="100" />
          <el-table-column prop="room_no" label="宿舍" width="100" />
          <el-table-column label="状态">
            <template #default="{ row }">
              <el-select v-model="checkRecords[row.id]" size="small" style="width: 130px">
                <el-option v-for="(l, k) in statuses" :key="k" :label="l" :value="k" />
              </el-select>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="异常记录" name="abnormal">
        <div class="toolbar">
          <el-button @click="loadAbnormal">刷新</el-button>
          <div class="spacer"></div>
          <el-button @click="handleExport">导出查寝台账</el-button>
        </div>
        <el-table :data="abnormalList" border stripe v-loading="loading">
          <el-table-column prop="check_date" label="日期" width="120" />
          <el-table-column prop="room_no" label="宿舍" width="100" />
          <el-table-column prop="student_no" label="学号" width="100" />
          <el-table-column prop="student_name" label="姓名" width="100" />
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.status === 'NOT_IN' ? 'danger' : 'warning'" size="small">{{ row.status_label }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="remark" label="备注" />
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getDormAssignments, batchDormCheck, getDormCheck, exportDormCheck } from '@/api'

const statuses = { IN: '在寝', LATE_BACK: '晚归', NOT_IN: '未归', APPROVED_OUT: '外宿' }
const activeTab = ref('check')
const loading = ref(false)
const checkDate = ref(new Date().toISOString().slice(0, 10))
const checkStudents = ref<any[]>([])
const checkRecords = reactive<Record<number, string>>({})
const abnormalList = ref<any[]>([])

const loadCheckStudents = async () => {
  loading.value = true
  try {
    const res: any = await getDormAssignments()
    checkStudents.value = res.data
    res.data.forEach((s: any) => { checkRecords[s.student_id] = 'IN' })
  } finally {
    loading.value = false
  }
}

const submitCheck = async () => {
  if (!checkDate.value) { ElMessage.warning('请选择日期'); return }
  // 映射 student_id
  const records: any = {}
  Object.keys(checkRecords).forEach((sid) => { records[sid] = checkRecords[Number(sid)] })
  await batchDormCheck({ check_date: checkDate.value, records })
  ElMessage.success('查寝已保存')
  loadAbnormal()
}

const loadAbnormal = async () => {
  loading.value = true
  try {
    const res: any = await getDormCheck({ abnormal: true, page: 1, size: 100 })
    abnormalList.value = res.data
  } finally {
    loading.value = false
  }
}

const handleExport = async () => {
  const res: any = await exportDormCheck()
  const url = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = url; a.download = 'dorm_check.xlsx'; a.click(); URL.revokeObjectURL(url)
}

onMounted(() => { loadCheckStudents(); loadAbnormal() })
</script>
