<template>
  <div class="page-container">
    <div class="chart-card">
      <h3>账号信息</h3>
      <div class="toolbar">
        <el-select v-model="startYear" placeholder="开始学年" style="width: 160px">
          <el-option v-for="y in yearOptions" :key="y" :label="`${y}-${y + 1} 学年`" :value="y" />
        </el-select>
        <el-select v-model="startSeq" placeholder="学期" style="width: 140px">
          <el-option label="第一学期" :value="1" />
          <el-option label="第二学期" :value="2" />
        </el-select>
        <el-button type="primary" @click="handleSaveStartSemester">保存开始学期</el-button>
      </div>
      <p class="tip">
        当前开始学期：<b>{{ account.start_semester ? startSemesterLabel(account.start_semester) : '未设置' }}</b>。
        从该学期起向后共 10 个学期（5 个学年），将作为班级全部学期。保存后各处学期下拉框将自动更新。
      </p>
    </div>

    <div class="chart-card">
      <h3>数据管理</h3>
      <div class="toolbar">
        <el-button type="danger" @click="handleClearData">清除所有数据</el-button>
        <el-button type="warning" plain @click="handleLogout">退出登录</el-button>
      </div>
      <p class="tip">清除数据将删除系统中所有已填写的内容（学生档案、班级组织、成绩、综合素质评价、荣誉证书等），此操作不可恢复。</p>
    </div>

    <div class="chart-card">
      <h3>数据备份</h3>
      <div class="toolbar">
        <el-button type="primary" @click="handleBackup">立即备份</el-button>
      </div>
      <el-table :data="backups" border stripe>
        <el-table-column prop="name" label="备份文件" />
        <el-table-column label="大小" width="120">
          <template #default="{ row }">{{ (row.size / 1024).toFixed(1) }} KB</template>
        </el-table-column>
        <el-table-column label="时间" width="200">
          <template #default="{ row }">{{ formatTime(row.mtime) }}</template>
        </el-table-column>
      </el-table>
    </div>

    <div class="chart-card">
      <h3>操作日志</h3>
      <el-table :data="logs" border stripe>
        <el-table-column prop="action" label="操作" width="120" />
        <el-table-column prop="detail" label="详情" />
        <el-table-column prop="created_at" label="时间" width="180" />
      </el-table>
    </div>

    <el-dialog v-model="clearDialog" title="清除所有数据" width="440px" :close-on-click-modal="false">
      <div class="clear-confirm">
        <el-alert type="error" :closable="false" show-icon title="此操作不可恢复！" description="将删除系统中所有已填写的数据，且无法恢复。" />
        <p class="clear-tip">请等待 {{ countdown }} 秒后确认操作</p>
      </div>
      <template #footer>
        <el-button @click="clearDialog = false">取消</el-button>
        <el-button type="danger" :disabled="countdown > 0" @click="confirmClear">确认清除</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="semesterDialog"
      title="选择开始学期"
      width="460px"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="false"
    >
      <el-alert type="info" :closable="false" show-icon title="首次使用，请设置开始担任班主任的学期" description="该学期将作为班级全部学期（共 10 个学期）的起点，设置后仍可在「账号信息」中修改。" />
      <div class="semester-form">
        <el-select v-model="startYear" placeholder="开始学年" style="width: 180px">
          <el-option v-for="y in yearOptions" :key="y" :label="`${y}-${y + 1} 学年`" :value="y" />
        </el-select>
        <el-select v-model="startSeq" placeholder="学期" style="width: 150px">
          <el-option label="第一学期" :value="1" />
          <el-option label="第二学期" :value="2" />
        </el-select>
      </div>
      <template #footer>
        <el-button type="primary" :loading="savingSemester" @click="handleSaveStartSemester">保存并进入系统</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAccount, updateAccount, getBackups, createBackup, getAuditLogs, clearData } from '@/api'
import { useUserStore } from '@/store/user'

const router = useRouter()
const userStore = useUserStore()

const account = ref<any>({})
const backups = ref<any[]>([])
const logs = ref<any[]>([])

const startYear = ref<number>(new Date().getFullYear())
const startSeq = ref<number>(1)

// 学年选项：当前年份前后 10 年
const yearOptions = Array.from({ length: 20 }, (_, i) => new Date().getFullYear() - 5 + i)

const startSemesterLabel = (sem: string) => {
  const parts = sem.split('-')
  const seq = Number(parts[parts.length - 1])
  return `${parts[0]}-${parts[1]} 学年${seq === 1 ? '第一学期' : '第二学期'}`
}

const handleSaveStartSemester = async () => {
  const sem = `${startYear.value}-${startYear.value + 1}-${startSeq.value}`
  savingSemester.value = true
  try {
    await updateAccount({ start_semester: sem })
    account.value.start_semester = sem
    userStore.updateStartSemester(sem)
    ElMessage.success('开始学期已保存，各处学期下拉框已自动更新')
    semesterDialog.value = false
  } finally {
    savingSemester.value = false
  }
}

const clearDialog = ref(false)
const countdown = ref(5)
let timer: any = null

const semesterDialog = ref(false)
const savingSemester = ref(false)

const handleClearData = () => {
  countdown.value = 5
  clearDialog.value = true
  if (timer) clearInterval(timer)
  timer = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      clearInterval(timer)
      timer = null
    }
  }, 1000)
}

const confirmClear = async () => {
  if (countdown.value > 0) return
  await clearData()
  ElMessage.success('数据已清除')
  clearDialog.value = false
  loadLogs()
}

const handleLogout = () => {
  ElMessageBox.confirm('确定退出登录吗？', '提示', { type: 'warning' }).then(() => {
    userStore.logout()
    router.push('/login')
  })
}

const handleBackup = async () => {
  const res: any = await createBackup()
  ElMessage.success(`备份完成：${res.data.name}`)
  loadBackups()
}

const formatTime = (ts: number) => new Date(ts * 1000).toLocaleString()

const loadBackups = async () => { const res: any = await getBackups(); backups.value = res.data }
const loadLogs = async () => { const res: any = await getAuditLogs({ page: 1, size: 20 }); logs.value = res.data }

onMounted(async () => {
  const a: any = await getAccount()
  account.value = a.data
  if (account.value.start_semester) {
    const parts = account.value.start_semester.split('-')
    startYear.value = Number(parts[0])
    startSeq.value = Number(parts[parts.length - 1])
    // 同步到 store，保证各处下拉框一致
    userStore.updateStartSemester(account.value.start_semester)
  } else {
    // 未设置开始学期，强制弹出选择框
    semesterDialog.value = true
  }
  loadBackups()
  loadLogs()
})

onBeforeUnmount(() => { if (timer) clearInterval(timer) })
</script>

<style scoped>
.tip {
  margin-top: 12px;
  color: #909399;
  font-size: 13px;
}
.clear-confirm {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.clear-tip {
  color: #e6a23c;
  font-size: 14px;
}
.semester-form {
  display: flex;
  gap: 12px;
  margin-top: 16px;
  justify-content: center;
}
</style>
