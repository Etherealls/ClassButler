<template>
  <div class="page-container">
    <div class="toolbar">
      <el-input v-model="semester" placeholder="学期" style="width: 180px" />
      <el-button type="primary" @click="load">查询</el-button>
      <div class="spacer"></div>
      <el-button @click="handleExport">导出预警名单</el-button>
    </div>

    <el-table :data="list" border stripe v-loading="loading">
      <el-table-column prop="student_no" label="学号" width="100" />
      <el-table-column prop="student_name" label="姓名" width="100" />
      <el-table-column prop="semester" label="学期" width="120" />
      <el-table-column prop="fail_count" label="挂科门数" width="90" />
      <el-table-column prop="average" label="平均分" width="90" />
      <el-table-column prop="prev_average" label="上学期均分" width="110" />
      <el-table-column prop="absent_count" label="旷课节次" width="90" />
      <el-table-column label="预警标签">
        <template #default="{ row }">
          <el-tag v-for="t in row.tags" :key="t" :type="t === '重点预警' ? 'danger' : 'warning'" size="small" style="margin-right: 4px">{{ t }}</el-tag>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getAlerts, exportAlerts } from '@/api'

const semester = ref('')
const list = ref<any[]>([])
const loading = ref(false)

const load = async () => {
  loading.value = true
  try {
    const res: any = await getAlerts({ semester: semester.value || undefined })
    list.value = res.data
  } finally {
    loading.value = false
  }
}

const handleExport = async () => {
  const res: any = await exportAlerts({ semester: semester.value || undefined })
  const url = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = url; a.download = 'alerts.xlsx'; a.click(); URL.revokeObjectURL(url)
}

onMounted(load)
</script>
