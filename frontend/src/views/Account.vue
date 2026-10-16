<template>
  <div class="page-container">
    <el-row :gutter="20">
      <el-col :span="12">
        <div class="chart-card">
          <h3>账号信息</h3>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="账号">{{ account.username }}</el-descriptions-item>
            <el-descriptions-item label="绑定班级">{{ account.class_name || '未绑定' }}</el-descriptions-item>
            <el-descriptions-item label="联系电话">{{ account.phone || '未填写' }}</el-descriptions-item>
          </el-descriptions>
        </div>
      </el-col>
      <el-col :span="12">
        <div class="chart-card">
          <h3>修改密码</h3>
          <el-form :model="pwdForm" label-width="90px">
            <el-form-item label="原密码"><el-input v-model="pwdForm.old_password" type="password" show-password /></el-form-item>
            <el-form-item label="新密码"><el-input v-model="pwdForm.new_password" type="password" show-password /></el-form-item>
            <el-form-item label="确认密码"><el-input v-model="confirmPwd" type="password" show-password /></el-form-item>
            <el-form-item><el-button type="primary" @click="handleChangePwd">修改密码</el-button></el-form-item>
          </el-form>
        </div>
      </el-col>
    </el-row>

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
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getAccount, changePassword, getBackups, createBackup, getAuditLogs } from '@/api'

const account = ref<any>({})
const backups = ref<any[]>([])
const logs = ref<any[]>([])
const pwdForm = reactive({ old_password: '', new_password: '' })
const confirmPwd = ref('')

const handleChangePwd = async () => {
  if (pwdForm.new_password.length < 6) { ElMessage.warning('密码至少 6 位'); return }
  if (pwdForm.new_password !== confirmPwd.value) { ElMessage.warning('两次密码不一致'); return }
  await changePassword(pwdForm)
  ElMessage.success('密码修改成功')
  pwdForm.old_password = ''; pwdForm.new_password = ''; confirmPwd.value = ''
}

const handleBackup = async () => {
  const res: any = await createBackup()
  ElMessage.success(`备份完成：${res.data.name}`)
  loadBackups()
}

const formatTime = (ts: number) => new Date(ts * 1000).toLocaleString()

const loadBackups = async () => { const res: any = await getBackups(); backups.value = res.data }

onMounted(async () => {
  const [a, l] = await Promise.all([getAccount(), getAuditLogs({ page: 1, size: 20 })])
  account.value = (a as any).data
  logs.value = (l as any).data
  loadBackups()
})
</script>
