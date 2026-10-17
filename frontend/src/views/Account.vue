<template>
  <div class="page-container">
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
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getBackups, createBackup, getAuditLogs, clearData } from '@/api'
import { useUserStore } from '@/store/user'

const router = useRouter()
const userStore = useUserStore()

const backups = ref<any[]>([])
const logs = ref<any[]>([])

const clearDialog = ref(false)
const countdown = ref(5)
let timer: any = null

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
</style>
