<template>
  <div class="page-container">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="批量点名" name="check">
        <div class="toolbar">
          <el-date-picker v-model="attDate" type="date" value-format="YYYY-MM-DD" placeholder="日期" />
          <el-select v-model="session" style="width: 150px">
            <el-option v-for="(l, k) in sessions" :key="k" :label="l" :value="k" />
          </el-select>
          <el-button type="primary" @click="loadStudents">加载学生</el-button>
          <div class="spacer"></div>
          <el-button type="success" @click="submitBatch">保存考勤</el-button>
        </div>
        <el-alert title="默认全班出勤，仅需标记异常学生" type="info" :closable="false" style="margin-bottom: 16px" />
        <el-table :data="studentList" border stripe v-loading="loading">
          <el-table-column prop="student_no" label="学号" width="100" />
          <el-table-column prop="name" label="姓名" width="100" />
          <el-table-column label="考勤状态">
            <template #default="{ row }">
              <el-select v-model="records[row.id]" size="small" style="width: 140px">
                <el-option v-for="(l, k) in statuses" :key="k" :label="l" :value="k" />
              </el-select>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="考勤台账" name="ledger">
        <div class="toolbar">
          <el-date-picker v-model="filterDate" type="date" value-format="YYYY-MM-DD" placeholder="按日期筛选" clearable @change="loadLedger" />
          <el-button @click="loadLedger">查询</el-button>
          <div class="spacer"></div>
          <el-button @click="handleExport">导出考勤台账</el-button>
        </div>
        <el-table :data="ledger" border stripe v-loading="loading">
          <el-table-column prop="att_date" label="日期" width="120" />
          <el-table-column prop="session_label" label="节次" width="100" />
          <el-table-column prop="student_no" label="学号" width="100" />
          <el-table-column prop="student_name" label="姓名" width="100" />
          <el-table-column prop="status_label" label="状态" width="100" />
          <el-table-column prop="remark" label="备注" />
        </el-table>
        <el-pagination class="pagination" :current-page="page" :page-size="size" :total="total" layout="total, prev, pager, next" @current-change="(p: number) => { page = p; loadLedger() }" />
      </el-tab-pane>

      <el-tab-pane label="出勤汇总" name="summary">
        <div class="toolbar">
          <el-button type="primary" @click="loadSummary">刷新汇总</el-button>
        </div>
        <el-table :data="summary" border stripe v-loading="loading">
          <el-table-column prop="student_no" label="学号" width="100" />
          <el-table-column prop="student_name" label="姓名" width="100" />
          <el-table-column prop="normal" label="出勤" width="70" />
          <el-table-column prop="late" label="迟到" width="70" />
          <el-table-column prop="early_leave" label="早退" width="70" />
          <el-table-column prop="absent" label="旷课" width="70" />
          <el-table-column prop="leave" label="请假" width="70" />
          <el-table-column label="出勤率" width="100">
            <template #default="{ row }">
              <span :style="{ color: row.attendance_rate < 0.8 ? '#f56c6c' : '#67c23a' }">{{ (row.attendance_rate * 100).toFixed(1) }}%</span>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getStudents, batchAttendance, getAttendance, getAttendanceSummary, exportAttendance } from '@/api'

const sessions = { MORNING_SELF: '早自习', AM: '上午课程', PM: '下午课程', EVENING_SELF: '晚自修', DAILY_EXERCISE: '出操' }
const statuses = { NORMAL: '出勤', LATE: '迟到', EARLY_LEAVE: '早退', ABSENT: '旷课', LEAVE_APPROVED: '请假', PUBLIC_LEAVE: '公假' }

const activeTab = ref('check')
const loading = ref(false)
const attDate = ref(new Date().toISOString().slice(0, 10))
const session = ref('AM')
const studentList = ref<any[]>([])
const records = reactive<Record<number, string>>({})
const ledger = ref<any[]>([])
const summary = ref<any[]>([])
const filterDate = ref('')
const page = ref(1)
const size = ref(50)
const total = ref(0)

const loadStudents = async () => {
  loading.value = true
  try {
    const res: any = await getStudents({ page: 1, size: 200 })
    studentList.value = res.data
    // 默认全部出勤
    studentList.value.forEach((s: any) => { records[s.id] = 'NORMAL' })
  } finally {
    loading.value = false
  }
}

const submitBatch = async () => {
  if (!attDate.value) { ElMessage.warning('请选择日期'); return }
  await batchAttendance({ att_date: attDate.value, session: session.value, records })
  ElMessage.success('考勤已保存')
}

const loadLedger = async () => {
  loading.value = true
  try {
    const res: any = await getAttendance({ att_date: filterDate.value || undefined, page: page.value, size: size.value })
    ledger.value = res.data
    total.value = res.total
  } finally {
    loading.value = false
  }
}

const loadSummary = async () => {
  loading.value = true
  try {
    const res: any = await getAttendanceSummary({})
    summary.value = res.data
  } finally {
    loading.value = false
  }
}

const handleExport = async () => {
  const res: any = await exportAttendance({})
  const url = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = url
  a.download = 'attendance.xlsx'
  a.click()
  URL.revokeObjectURL(url)
}

onMounted(() => { loadStudents(); loadLedger(); loadSummary() })
</script>

<style scoped>
.pagination { margin-top: 16px; justify-content: flex-end; }
</style>
