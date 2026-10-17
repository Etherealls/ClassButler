<template>
  <div class="page-container">
    <div class="toolbar">
      <el-input v-model="semester" placeholder="学期，如 2024-2025-1" style="width: 180px" />
      <el-select v-model="level" placeholder="评价等级" style="width: 140px">
        <el-option v-for="l in levels" :key="l" :label="l" :value="l" />
      </el-select>
      <el-button type="primary" @click="handleSubmit">提交</el-button>
      <div class="spacer"></div>
      <el-button type="success" @click="handleExport">导出 Excel</el-button>
    </div>

    <el-alert type="info" :closable="false" style="margin-bottom: 16px">
      计分规则：合计 800–950 为优秀、700–799 为良好、600–699 为合格、600 以下为不合格；单个素质最高 190 分，五项尽量平均，所有得分均为整数。
      提交时：若填写了「班级排名」或「综合评价等级」，系统将自动计算单素质得分并排序；若填写了单素质得分，系统将自动计算合计与评价等级并排序。班级排名为选填。
    </el-alert>

    <el-table :data="list" border stripe v-loading="loading" max-height="600" row-key="student_id">
      <el-table-column type="index" label="序号" width="60" />
      <el-table-column prop="student_name" label="学生姓名" width="110" fixed="left" />
      <el-table-column prop="student_no" label="学生学号" width="120" />
      <el-table-column label="德育" width="100">
        <template #default="{ row }">
          <el-input-number v-model="row.moral" :min="0" :max="190" :precision="0" :step="1" size="small" controls-position="right" />
        </template>
      </el-table-column>
      <el-table-column label="智育" width="100">
        <template #default="{ row }">
          <el-input-number v-model="row.intellect" :min="0" :max="190" :precision="0" :step="1" size="small" controls-position="right" />
        </template>
      </el-table-column>
      <el-table-column label="体育" width="100">
        <template #default="{ row }">
          <el-input-number v-model="row.sport" :min="0" :max="190" :precision="0" :step="1" size="small" controls-position="right" />
        </template>
      </el-table-column>
      <el-table-column label="美育" width="100">
        <template #default="{ row }">
          <el-input-number v-model="row.art" :min="0" :max="190" :precision="0" :step="1" size="small" controls-position="right" />
        </template>
      </el-table-column>
      <el-table-column label="劳育" width="100">
        <template #default="{ row }">
          <el-input-number v-model="row.labor" :min="0" :max="190" :precision="0" :step="1" size="small" controls-position="right" />
        </template>
      </el-table-column>
      <el-table-column prop="total" label="合计" width="80" />
      <el-table-column label="班级排名" width="110">
        <template #default="{ row }">
          <el-input-number v-model="row.rank" :min="1" :max="999" :precision="0" :step="1" size="small" controls-position="right" placeholder="选填" />
        </template>
      </el-table-column>
      <el-table-column label="综合评价等级" width="130">
        <template #default="{ row }">
          <el-select v-model="row.level" size="small" clearable placeholder="选填">
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

// 判断某行是否填写了单素质得分（任一单项有值）
const hasScore = (row: any) => {
  return row.moral !== null && row.moral !== undefined && row.moral !== ''
    || row.intellect !== null && row.intellect !== undefined && row.intellect !== ''
    || row.sport !== null && row.sport !== undefined && row.sport !== ''
    || row.art !== null && row.art !== undefined && row.art !== ''
    || row.labor !== null && row.labor !== undefined && row.labor !== ''
}

// 提交：分别处理"按排名/等级生成"与"按手动得分计算"
const handleSubmit = async () => {
  if (!semester.value) { ElMessage.warning('请输入学期'); return }

  const manualRows: any[] = []   // 填写了单素质得分的学生
  const rankRows: any[] = []     // 填写了班级排名的学生（选填等级）
  const levelRows: any[] = []    // 填写了等级但未填排名/得分的学生

  for (const row of list.value) {
    if (hasScore(row)) {
      manualRows.push(row)
    } else if (row.rank !== null && row.rank !== undefined && row.rank !== '') {
      rankRows.push(row)
    } else if (row.level) {
      levelRows.push(row)
    }
  }

  if (!manualRows.length && !rankRows.length && !levelRows.length) {
    ElMessage.warning('请先填写得分、班级排名或评价等级')
    return
  }

  loading.value = true
  try {
    // 1. 按排名生成（需要等级，若未填等级则用顶部选择的等级）
    if (rankRows.length) {
      const rankMap: any = {}
      rankRows.forEach((r) => { rankMap[String(r.student_id)] = Number(r.rank) })
      await evaluateQuality({
        semester: semester.value,
        level: level.value || '优秀',
        student_ids: rankRows.map((r) => r.student_id),
        rank_map: rankMap,
      })
    }
    // 2. 按等级生成（未填排名的学生）
    if (levelRows.length) {
      await evaluateQuality({
        semester: semester.value,
        level: level.value || '优秀',
        student_ids: levelRows.map((r) => r.student_id),
      })
    }
    // 3. 手动得分：逐个提交，后端计算合计和等级
    for (const row of manualRows) {
      const moral = Number(row.moral) || 0
      const intellect = Number(row.intellect) || 0
      const sport = Number(row.sport) || 0
      const art = Number(row.art) || 0
      const labor = Number(row.labor) || 0
      await manualQuality({
        student_id: row.student_id,
        semester: semester.value,
        level: row.level || null,
        moral, intellect, sport, art, labor,
      })
    }
    ElMessage.success('提交成功，已自动计算得分并排序')
    await load()
  } finally {
    loading.value = false
  }
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
