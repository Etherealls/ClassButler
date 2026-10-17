<template>
  <div>
    <!-- 工具栏：学期 + 类型切换 + 节数设置 -->
    <div class="toolbar">
      <el-select v-model="semester" placeholder="选择学期" style="width: 220px" @change="onSemesterChange">
        <el-option v-for="s in semesters" :key="s.value" :label="s.label" :value="s.value" :disabled="!s.editable && !s.readonly" />
      </el-select>
      <el-select v-if="showTypeSelect" v-model="subType" placeholder="课程表类型" style="width: 180px" @change="load">
        <el-option label="班级课程表" value="class" />
        <el-option label="班主任课程表" value="teacher" />
      </el-select>
      <span style="margin-left: 8px">上午节数：</span>
      <el-input-number v-model="morningCount" :min="1" :max="8" size="small" />
      <span style="margin-left: 8px">下午节数：</span>
      <el-input-number v-model="afternoonCount" :min="0" :max="8" size="small" />
      <el-button v-if="!isReadonly" type="primary" @click="saveSetting">保存节数设置</el-button>
      <el-upload v-if="!isReadonly" :show-file-list="false" :before-upload="handleImport" accept=".xlsx">
        <el-button>导入排课数据</el-button>
      </el-upload>
      <el-button @click="downloadTemplate">下载导入模板</el-button>
      <div class="spacer"></div>
      <el-button type="success" @click="exportSchedule">导出课程表</el-button>
    </div>

    <el-alert v-if="isReadonly" type="warning" :closable="false" style="margin-bottom: 12px">
      当前为历史学期，课程表仅可查看，不可修改。
    </el-alert>
    <el-alert v-else type="info" :closable="false" style="margin-bottom: 12px">
      点击任意课程单元格即可编辑课程、任课老师与上课地点；点击左侧「第几节」可修改该节的时间段。
    </el-alert>

    <!-- 课程表表格 -->
    <div class="schedule-wrap" v-loading="loading">
      <el-table :data="rows" border :span-method="spanMethod" class="schedule-table">
        <el-table-column label="节次" width="120" align="center" fixed="left">
          <template #default="{ row }">
            <div v-if="row.isMorningHeader" class="half-header">上午</div>
            <div v-else-if="row.isAfternoonHeader" class="half-header">下午</div>
            <div v-else class="period-cell">
              <span class="period-no">第{{ row.periodLabel }}节</span>
              <el-input
                v-if="!isReadonly"
                v-model="periods[row.periodIndex]"
                size="small"
                class="period-time-input"
                placeholder="时间段"
              />
              <span v-else class="period-time">{{ periods[row.periodIndex] || '' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column v-for="d in 7" :key="d" :label="weekdayLabel(d)" align="center" min-width="130">
          <template #default="{ row }">
            <template v-if="!row.isHeader">
              <div class="course-cell" @click="editCell(d, row.periodIndex)">
                <div class="course-name">{{ cellText(d, row.periodIndex) }}</div>
                <div v-if="cellTeacher(d, row.periodIndex)" class="course-teacher">{{ cellTeacher(d, row.periodIndex) }}</div>
                <div v-if="cellLocation(d, row.periodIndex)" class="course-location">{{ cellLocation(d, row.periodIndex) }}</div>
              </div>
            </template>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 编辑单元格对话框 -->
    <el-dialog v-model="cellDialog" title="编辑课程" width="420px">
      <el-form label-width="80px">
        <el-form-item label="课程名"><el-input v-model="cellForm.course_name" placeholder="如：语文" /></el-form-item>
        <el-form-item label="任课老师"><el-input v-model="cellForm.teacher_name" placeholder="选填" /></el-form-item>
        <el-form-item label="上课地点"><el-input v-model="cellForm.location" placeholder="选填" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button v-if="cellForm.existing" type="danger" plain @click="clearCell">清空该节</el-button>
        <el-button @click="cellDialog = false">取消</el-button>
        <el-button type="primary" @click="saveCell">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getSemesters, getScheduleSetting, saveScheduleSetting,
  getScheduleEntries, saveScheduleEntry, deleteScheduleEntry,
  importSchedule, downloadScheduleTemplate,
} from '@/api'

const props = defineProps<{ type: string; semester: string; showTypeSelect?: boolean }>()

const semester = ref(props.semester)
const subType = ref(props.type === 'class' ? 'class' : 'training')
const semesters = ref<any[]>([])
const morningCount = ref(4)
const afternoonCount = ref(4)
const periods = ref<string[]>([])
const settingId = ref<number | null>(null)
const entries = ref<any[]>([])
const loading = ref(false)

const weekdayLabel = (d: number) => ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][d - 1]

const isReadonly = computed(() => {
  const s = semesters.value.find((x) => x.value === semester.value)
  return !!s?.readonly
})

const totalCount = computed(() => morningCount.value + afternoonCount.value)

// 表格行：包含上午/下午表头行 + 每节一行
const rows = computed(() => {
  const r: any[] = []
  r.push({ isHeader: true, isMorningHeader: true, periodIndex: -1 })
  for (let i = 0; i < morningCount.value; i++) {
    r.push({ isHeader: false, periodIndex: i, periodLabel: i + 1, isMorning: true })
  }
  if (afternoonCount.value > 0) {
    r.push({ isHeader: true, isAfternoonHeader: true, periodIndex: -1 })
    for (let i = 0; i < afternoonCount.value; i++) {
      r.push({ isHeader: false, periodIndex: morningCount.value + i, periodLabel: morningCount.value + i + 1, isMorning: false })
    }
  }
  return r
})

// 表头行跨整行
const spanMethod = ({ row, columnIndex }: any) => {
  if (row.isHeader && columnIndex === 0) return [1, 8]
  if (row.isHeader) return [0, 0]
  return [1, 1]
}

// 单元格数据查询
const entryMap = computed(() => {
  const m: Record<string, any> = {}
  for (const e of entries.value) {
    m[`${e.weekday}-${e.period_index}`] = e
  }
  return m
})
const cellText = (weekday: number, periodIndex: number) => {
  const e = entryMap.value[`${weekday}-${periodIndex}`]
  return e?.course_name || ''
}
const cellTeacher = (weekday: number, periodIndex: number) => entryMap.value[`${weekday}-${periodIndex}`]?.teacher_name || ''
const cellLocation = (weekday: number, periodIndex: number) => entryMap.value[`${weekday}-${periodIndex}`]?.location || ''

const load = async () => {
  if (!semester.value) return
  loading.value = true
  try {
    const res: any = await getScheduleSetting({ type: subType.value, semester: semester.value })
    const d = res.data
    settingId.value = d.id
    morningCount.value = d.morning_count
    afternoonCount.value = d.afternoon_count
    periods.value = [...(d.periods || [])]
    if (d.id) {
      const er: any = await getScheduleEntries(d.id)
      entries.value = er.data
    } else {
      entries.value = []
    }
  } finally {
    loading.value = false
  }
}

const onSemesterChange = () => load()

// 导入排课数据
const handleImport = async (file: File) => {
  if (!semester.value) { ElMessage.warning('请先选择学期'); return false }
  if (isReadonly.value) { ElMessage.warning('历史学期不可导入'); return false }
  const fd = new FormData()
  fd.append('file', file)
  const res: any = await importSchedule(fd, { type: subType.value, semester: semester.value })
  const { success, skipped, errors } = res.data
  let msg = res.message || `导入成功 ${success} 格`
  if (errors && errors.length) {
    ElMessage.warning(`${msg}，失败 ${errors.length} 行：${errors[0].reason}`)
  } else {
    ElMessage.success(msg)
  }
  load()
  return false
}

const downloadTemplate = async () => {
  const res: any = await downloadScheduleTemplate()
  const url = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = url; a.download = '课程表导入模板.xlsx'; a.click(); URL.revokeObjectURL(url)
}

const saveSetting = async () => {
  if (!semester.value) { ElMessage.warning('请先选择学期'); return }
  const res: any = await saveScheduleSetting({
    type: subType.value,
    semester: semester.value,
    morning_count: morningCount.value,
    afternoon_count: afternoonCount.value,
    periods: periods.value,
  })
  settingId.value = res.data.id
  ElMessage.success('节数设置已保存')
  load()
}

// 编辑单元格
const cellDialog = ref(false)
const cellForm = ref<any>({ weekday: 0, period_index: 0, course_name: '', teacher_name: '', location: '', existing: false })

const editCell = (weekday: number, periodIndex: number) => {
  if (isReadonly.value) return
  const e = entryMap.value[`${weekday}-${periodIndex}`]
  cellForm.value = {
    weekday,
    period_index: periodIndex,
    course_name: e?.course_name || '',
    teacher_name: e?.teacher_name || '',
    location: e?.location || '',
    existing: !!e,
  }
  cellDialog.value = true
}

const saveCell = async () => {
  if (!settingId.value) {
    // 尚未保存设置，先保存设置
    const res: any = await saveScheduleSetting({
      type: subType.value, semester: semester.value,
      morning_count: morningCount.value, afternoon_count: afternoonCount.value, periods: periods.value,
    })
    settingId.value = res.data.id
  }
  await saveScheduleEntry({
    setting_id: settingId.value,
    weekday: cellForm.value.weekday,
    period_index: cellForm.value.period_index,
    course_name: cellForm.value.course_name || '',
    teacher_name: cellForm.value.teacher_name || '',
    location: cellForm.value.location || '',
  })
  cellDialog.value = false
  ElMessage.success('课程已保存')
  load()
}

const clearCell = async () => {
  const e = entryMap.value[`${cellForm.value.weekday}-${cellForm.value.period_index}`]
  if (e?.id) await deleteScheduleEntry(e.id)
  cellDialog.value = false
  ElMessage.success('已清空该节')
  load()
}

// 导出课程表为 CSV
const exportSchedule = () => {
  if (!semester.value) { ElMessage.warning('请先选择学期'); return }
  const headers = ['节次', '周一', '周二', '周三', '周四', '周五', '周六', '周日']
  const lines: string[] = [headers.join(',')]
  rows.value.forEach((row) => {
    if (row.isHeader) {
      lines.push([row.isMorningHeader ? '上午' : '下午', '', '', '', '', '', '', ''].join(','))
    } else {
      const cells = [`第${row.periodLabel}节 ${periods.value[row.periodIndex] || ''}`]
      for (let d = 1; d <= 7; d++) {
        const t = cellText(d, row.periodIndex)
        const loc = cellLocation(d, row.periodIndex)
        cells.push(t + (loc ? `@${loc}` : ''))
      }
      lines.push(cells.join(','))
    }
  })
  const csv = '\ufeff' + lines.join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${subType.value === 'teacher' ? '班主任课程表' : '课程表'}_${semester.value}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

onMounted(async () => {
  const res: any = await getSemesters()
  semesters.value = res.data.semesters
  if (!semester.value) {
    semester.value = res.data.editable_semester || res.data.current_semester || ''
  }
  load()
})
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}
.spacer {
  flex: 1;
}
.half-header {
  background: #f5f7fa;
  color: #409eff;
  font-weight: 600;
  padding: 6px 0;
}
.period-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 4px 0;
}
.period-no {
  font-weight: 600;
  color: #303133;
  white-space: nowrap;
}
.period-time {
  font-size: 12px;
  color: #909399;
}
.period-time-input {
  width: 100px;
}
.course-cell {
  min-height: 48px;
  padding: 6px 4px;
  cursor: pointer;
  border-radius: 4px;
  transition: background 0.2s;
}
.course-cell:hover {
  background: #ecf5ff;
}
.course-name {
  font-weight: 600;
  color: #303133;
}
.course-teacher {
  font-size: 12px;
  color: #606266;
}
.course-location {
  font-size: 12px;
  color: #909399;
}
.schedule-wrap {
  overflow-x: auto;
}
</style>
