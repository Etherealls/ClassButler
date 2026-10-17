<template>
  <div>
    <div class="toolbar">
      <el-button-group>
        <el-button @click="changeMonth(-1)">上个月</el-button>
        <el-button @click="changeMonth(1)">下个月</el-button>
      </el-button-group>
      <el-button @click="goToday">回到今天</el-button>
      <span class="month-title">{{ year }} 年 {{ month }} 月</span>
      <div class="spacer"></div>
      <el-upload :show-file-list="false" :before-upload="handleImageImport" accept=".jpg,.jpeg,.png">
        <el-button type="warning" plain :loading="importing">导入校历图片</el-button>
      </el-upload>
      <el-button type="primary" @click="openEventDialog()">添加校历事件</el-button>
      <div class="legend">
        <span class="legend-item"><i class="dot" style="background:#409eff"></i>上课</span>
        <span class="legend-item"><i class="dot" style="background:#67c23a"></i>假期</span>
        <span class="legend-item"><i class="dot" style="background:#f56c6c"></i>考试</span>
      </div>
    </div>

    <el-alert type="info" :closable="false" style="margin-bottom: 12px">
      校历用颜色区分上课、假期、考试。点击任意日期可查看/新增/修改事件。
    </el-alert>

    <!-- 日历网格 -->
    <div class="calendar" v-loading="loading">
      <div class="cal-header">
        <div v-for="w in weekdayNames" :key="w" class="cal-header-cell">{{ w }}</div>
      </div>
      <div class="cal-grid">
        <div
          v-for="cell in cells"
          :key="cell.key"
          class="cal-cell"
          :class="{ 'is-other': !cell.inMonth }"
          @click="openEventDialog(cell.date)"
        >
          <div class="cal-date">{{ cell.day }}</div>
          <div class="cal-tags">
            <el-tag
              v-for="ev in cell.events"
              :key="ev.id"
              size="small"
              :type="tagType(ev.type)"
              class="cal-tag"
              @click.stop="editEvent(ev)"
            >
              {{ ev.type_label }}{{ ev.note ? '·' + ev.note : '' }}
            </el-tag>
          </div>
        </div>
      </div>
    </div>

    <!-- 事件编辑对话框 -->
    <el-dialog v-model="eventDialog" :title="eventForm.id ? '编辑校历事件' : '添加校历事件'" width="420px">
      <el-form label-width="80px">
        <el-form-item label="日期">
          <el-date-picker v-model="eventForm.date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="eventForm.type" style="width: 100%">
            <el-option label="上课" value="class" />
            <el-option label="假期" value="holiday" />
            <el-option label="考试" value="exam" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="eventForm.note" placeholder="如：国庆节放假 / 期中考试" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button v-if="eventForm.id" type="danger" plain @click="removeEvent">删除</el-button>
        <el-button @click="eventDialog = false">取消</el-button>
        <el-button type="primary" @click="saveEvent">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getCalendarEvents, saveCalendarEvent, deleteCalendarEvent, importCalendarImage } from '@/api'

const weekdayNames = ['日', '一', '二', '三', '四', '五', '六']

const today = new Date()
const year = ref(today.getFullYear())
const month = ref(today.getMonth() + 1) // 1-12
const events = ref<any[]>([])
const loading = ref(false)

// 事件按日期分组
const eventMap = computed(() => {
  const m: Record<string, any[]> = {}
  for (const e of events.value) {
    const key = e.date
    if (!m[key]) m[key] = []
    m[key].push(e)
  }
  return m
})

// 生成日历格子
const cells = computed(() => {
  const first = new Date(year.value, month.value - 1, 1)
  const startWeekday = first.getDay() // 0=周日
  const daysInMonth = new Date(year.value, month.value, 0).getDate()
  const cells: any[] = []
  // 前导空白（上月日期）
  const prevDays = new Date(year.value, month.value - 1, 0).getDate()
  for (let i = startWeekday - 1; i >= 0; i--) {
    const d = prevDays - i
    const date = fmt(new Date(year.value, month.value - 2, d))
    cells.push({ key: 'prev-' + d, day: d, inMonth: false, date, events: eventMap.value[date] || [] })
  }
  for (let d = 1; d <= daysInMonth; d++) {
    const date = fmt(new Date(year.value, month.value - 1, d))
    cells.push({ key: 'cur-' + d, day: d, inMonth: true, date, events: eventMap.value[date] || [] })
  }
  // 补齐到整周
  const total = cells.length
  const remain = (7 - (total % 7)) % 7
  for (let i = 1; i <= remain; i++) {
    const date = fmt(new Date(year.value, month.value, i))
    cells.push({ key: 'next-' + i, day: i, inMonth: false, date, events: eventMap.value[date] || [] })
  }
  return cells
})

const fmt = (d: Date) => {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${dd}`
}

const tagType = (t: string) => (t === 'class' ? 'primary' : t === 'holiday' ? 'success' : 'danger')

const changeMonth = (delta: number) => {
  let m = month.value + delta
  let y = year.value
  if (m < 1) { m = 12; y-- }
  if (m > 12) { m = 1; y++ }
  year.value = y
  month.value = m
  load()
}

const goToday = () => {
  year.value = today.getFullYear()
  month.value = today.getMonth() + 1
  load()
}

const load = async () => {
  loading.value = true
  try {
    const start = fmt(new Date(year.value, month.value - 1, 1))
    const end = fmt(new Date(year.value, month.value, 0))
    // 拉取整月（含前后若干天）
    const res: any = await getCalendarEvents({ start: `${year.value}-01-01`, end: `${year.value}-12-31` })
    events.value = res.data
  } finally {
    loading.value = false
  }
}

// 事件编辑
const eventDialog = ref(false)
const eventForm = ref<any>({ id: null, date: '', type: 'class', note: '' })

const openEventDialog = (date?: string) => {
  eventForm.value = { id: null, date: date || fmt(new Date()), type: 'class', note: '' }
  eventDialog.value = true
}

const editEvent = (ev: any) => {
  eventForm.value = { id: ev.id, date: ev.date, type: ev.type, note: ev.note || '' }
  eventDialog.value = true
}

const saveEvent = async () => {
  if (!eventForm.value.date) { ElMessage.warning('请选择日期'); return }
  await saveCalendarEvent({
    date: eventForm.value.date,
    type: eventForm.value.type,
    note: eventForm.value.note || '',
  })
  eventDialog.value = false
  ElMessage.success('校历事件已保存')
  load()
}

const removeEvent = async () => {
  if (eventForm.value.id) await deleteCalendarEvent(eventForm.value.id)
  eventDialog.value = false
  ElMessage.success('已删除')
  load()
}

// 图片导入校历
const importing = ref(false)
const handleImageImport = async (file: File) => {
  importing.value = true
  try {
    const fd = new FormData()
    fd.append('file', file)
    const res: any = await importCalendarImage(fd, {})
    const { stats, warnings } = res.data || {}
    let msg = res.message || '导入成功'
    ElMessage.success(msg)
    if (warnings && warnings.length) {
      ElMessage.warning({ message: `部分内容被忽略：${warnings[0]}${warnings.length > 1 ? ` 等 ${warnings.length} 条` : ''}`, duration: 6000 })
    }
    load()
  } finally {
    importing.value = false
  }
  return false
}

onMounted(load)
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
.month-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}
.legend {
  display: flex;
  align-items: center;
  gap: 12px;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #606266;
}
.dot {
  width: 12px;
  height: 12px;
  border-radius: 3px;
  display: inline-block;
}
.calendar {
  border: 1px solid #ebeef5;
  border-radius: 6px;
  overflow: hidden;
}
.cal-header {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  background: #f5f7fa;
}
.cal-header-cell {
  padding: 10px;
  text-align: center;
  font-weight: 600;
  color: #606266;
  border-right: 1px solid #ebeef5;
}
.cal-header-cell:last-child {
  border-right: none;
}
.cal-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
}
.cal-cell {
  min-height: 90px;
  border-right: 1px solid #ebeef5;
  border-bottom: 1px solid #ebeef5;
  padding: 6px;
  cursor: pointer;
  transition: background 0.2s;
  overflow: hidden;
}
.cal-cell:nth-child(7n) {
  border-right: none;
}
.cal-cell:hover {
  background: #ecf5ff;
}
.cal-cell.is-other {
  background: #fafafa;
  color: #c0c4cc;
}
.cal-date {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 4px;
  color: #303133;
}
.is-other .cal-date {
  color: #c0c4cc;
}
.cal-tags {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.cal-tag {
  margin: 0;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
