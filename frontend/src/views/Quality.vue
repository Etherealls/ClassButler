<template>
  <div class="page-container">
    <div class="toolbar">
      <el-input v-model="semester" placeholder="学期，如 2024-2025-1" style="width: 180px" />
      <el-select v-model="level" placeholder="评价等级" style="width: 140px">
        <el-option v-for="l in levels" :key="l" :label="l" :value="l" />
      </el-select>
      <el-button type="primary" @click="handleAutoEvaluate">按等级自动得分</el-button>
      <div class="spacer"></div>
      <el-button type="success" @click="handleExport">导出 Excel</el-button>
    </div>

    <el-alert type="info" :closable="false" style="margin-bottom: 16px">
      计分规则：合计 800–950 为优秀、700–799 为良好、600–699 为合格、600 以下为不合格；单个素质最高 190 分，五项尽量平均。
      选中学生后可按等级批量生成得分，也可点击每行「等级」单独调整，系统将自动生成对应分数并自动排名。
    </el-alert>

    <el-table :data="list" border stripe v-loading="loading" max-height="600" @selection-change="onSelectionChange" row-key="student_id">
      <el-table-column type="selection" width="46" />
      <el-table-column type="index" label="序号" width="60" />
      <el-table-column prop="student_name" label="学生姓名" width="110" fixed="left" />
      <el-table-column prop="student_no" label="学生学号" width="120" />
      <el-table-column label="德育" width="90">
        <template #default="{ row }">
          <el-input-number v-model="row.moral" :min="0" :max="190" :precision="1" size="small" controls-position="right" @change="(v:any) => onScoreChange(row)" />
        </template>
      </el-table-column>
      <el-table-column label="智育" width="90">
        <template #default="{ row }">
          <el-input-number v-model="row.intellect" :min="0" :max="190" :precision="1" size="small" controls-position="right" @change="(v:any) => onScoreChange(row)" />
        </template>
      </el-table-column>
      <el-table-column label="体育" width="90">
        <template #default="{ row }">
          <el-input-number v-model="row.sport" :min="0" :max="190" :precision="1" size="small" controls-position="right" @change="(v:any) => onScoreChange(row)" />
        </template>
      </el-table-column>
      <el-table-column label="美育" width="90">
        <template #default="{ row }">
          <el-input-number v-model="row.art" :min="0" :max="190" :precision="1" size="small" controls-position="right" @change="(v:any) => onScoreChange(row)" />
        </template>
      </el-table-column>
      <el-table-column label="劳育" width="90">
        <template #default="{ row }">
          <el-input-number v-model="row.labor" :min="0" :max="190" :precision="1" size="small" controls-position="right" @change="(v:any) => onScoreChange(row)" />
        </template>
      </el-table-column>
      <el-table-column prop="total" label="合计" width="80" />
      <el-table-column prop="rank" label="班级排名" width="90" />
      <el-table-column label="综合评价等级" width="130">
        <template #default="{ row }">
          <el-select v-model="row.level" size="small" @change="(v:string) => onLevelChange(row, v)">
            <el-option v-for="l in levels" :key="l" :label="l" :value="l" />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="70" fixed="right">
        <template #default="{ row }">
          <el-button link type="danger" size="small" @click="handleClear(row)">清除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getQuality, evaluateQuality, manualQuality, deleteQuality, exportQuality } from '@/api'

const levels = ['优秀', '良好', '合格', '不合格']
const semester = ref('')
const level = ref('优秀')
const list = ref<any[]>([])
const loading = ref(false)
const selectedRows = ref<any[]>([])

const onSelectionChange = (rows: any[]) => { selectedRows.value = rows }

const load = async () => {
  if (!semester.value) { ElMessage.warning('请输入学期'); return }
  loading.value = true
  try {
    const res: any = await getQuality({ semester: semester.value })
    list.value = res.data
  } finally {
    loading.value = false
  }
}

// 按等级自动生成得分（作用于选中的学生，未选中则全班级）
const handleAutoEvaluate = async () => {
  if (!semester.value) { ElMessage.warning('请输入学期'); return }
  if (!level.value) { ElMessage.warning('请选择评价等级'); return }
  const studentIds = selectedRows.value.map((r) => r.student_id)
  const tip = studentIds.length
    ? `将按「${level.value}」为选中的 ${studentIds.length} 名学生生成得分，是否继续？`
    : `将按「${level.value}」为全班学生生成得分，是否继续？`
  const res: any = await evaluateQuality({ semester: semester.value, level: level.value, student_ids: studentIds.length ? studentIds : null })
  ElMessage.success(res.message || '已生成')
  await load()
}

// 单独调整某行等级 -> 重新按该等级生成该生得分
const onLevelChange = async (row: any, v: string) => {
  if (!row.student_id || !semester.value) return
  const res: any = await evaluateQuality({ semester: semester.value, level: v, student_ids: [row.student_id] })
  ElMessage.success(`已按「${v}」重新生成 ${row.student_name} 的得分`)
  await load()
}

// 手动修改单项得分 -> 合计自动重算并保存（等级自动判定）
const onScoreChange = async (row: any) => {
  if (!row.student_id || !semester.value) return
  const moral = Number(row.moral) || 0
  const intellect = Number(row.intellect) || 0
  const sport = Number(row.sport) || 0
  const art = Number(row.art) || 0
  const labor = Number(row.labor) || 0
  await manualQuality({ student_id: row.student_id, semester: semester.value, moral, intellect, sport, art, labor })
  await load()
}

// 清除某学生评价
const handleClear = async (row: any) => {
  if (!row.student_id) return
  await deleteQuality(row.student_id, semester.value)
  ElMessage.success('已清除')
  await load()
}

const handleExport = async () => {
  if (!semester.value) { ElMessage.warning('请输入学期'); return }
  const res: any = await exportQuality({ semester: semester.value })
  const url = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = url; a.download = `综合素质评价_${semester.value}.xlsx`; a.click(); URL.revokeObjectURL(url)
}

onMounted(() => {
  const now = new Date()
  const y = now.getFullYear()
  const m = now.getMonth() + 1
  semester.value = m >= 8 ? `${y}-${y + 1}-1` : `${y - 1}-${y}-2`
  load()
})
</script>
