<template>
  <div class="page-container">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="学生干部" name="cadre">
        <div class="toolbar">
          <el-button type="primary" @click="openCadreDialog">登记干部</el-button>
        </div>
        <el-table :data="cadres" border stripe v-loading="loading">
          <el-table-column prop="student_name" label="姓名" width="100" />
          <el-table-column prop="student_no" label="学号" width="120" />
          <el-table-column prop="position" label="职务" />
          <el-table-column prop="start_date" label="任职开始" width="120" />
          <el-table-column prop="end_date" label="任职结束" width="120" />
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="宿舍管理" name="dorm">
        <div class="toolbar">
          <el-button type="primary" @click="openDormDialog">分配宿舍</el-button>
          <el-button @click="openRoomDialog">添加宿舍</el-button>
        </div>
        <el-table :data="dormAssignments" border stripe v-loading="loading">
          <el-table-column prop="student_name" label="姓名" width="100" />
          <el-table-column prop="student_no" label="学号" width="120" />
          <el-table-column prop="room_no" label="宿舍号" width="120" />
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="座位表" name="seat">
        <div class="toolbar">
          <span>行：</span>
          <el-input-number v-model="seatRows" :min="1" :max="10" />
          <span style="margin-left: 12px">列：</span>
          <el-input-number v-model="seatCols" :min="1" :max="10" />
          <el-button type="primary" @click="initSeatGrid">生成座位网格</el-button>
          <el-button type="success" @click="saveSeat">保存座位表</el-button>
        </div>
        <div class="seat-grid" :style="{ gridTemplateColumns: `repeat(${seatCols}, 120px)` }">
          <div v-for="(cell, i) in seatGrid" :key="i" class="seat-cell">
            <el-select v-model="cell.studentId" filterable clearable placeholder="空位" @change="reassignSeat(i, cell.studentId)">
              <el-option v-for="s in allStudents" :key="s.id" :label="s.name" :value="s.id" />
            </el-select>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="值日排班" name="duty">
        <div class="toolbar">
          <el-select v-model="dutyWeekdayFilter" placeholder="按星期筛选" clearable style="width: 140px" @change="loadDuty">
            <el-option v-for="i in 7" :key="i" :label="weekdayLabel(i)" :value="i" />
          </el-select>
          <el-button type="primary" @click="openDutyDialog">添加值日安排</el-button>
        </div>
        <el-table :data="dutyList" border stripe v-loading="loading">
          <el-table-column label="星期" width="100">
            <template #default="{ row }">{{ weekdayLabel(row.weekday) }}</template>
          </el-table-column>
          <el-table-column label="值日生">
            <template #default="{ row }">
              <el-tag v-for="s in row.students" :key="s.id" size="small" style="margin: 2px 4px 2px 0">
                {{ s.name }}{{ s.job ? '（' + s.job + '）' : '' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="note" label="备注" />
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="cadreDialog" title="登记学生干部" width="480px">
      <el-form label-width="80px">
        <el-form-item label="学生"><el-select v-model="cadreForm.student_id" filterable><el-option v-for="s in allStudents" :key="s.id" :label="s.name" :value="s.id" /></el-select></el-form-item>
        <el-form-item label="职务"><el-input v-model="cadreForm.position" placeholder="如：班长" /></el-form-item>
        <el-form-item label="任职日期"><el-date-picker v-model="cadreForm.start_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="cadreDialog = false">取消</el-button><el-button type="primary" @click="saveCadre">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="dormDialog" title="分配宿舍" width="480px">
      <el-form label-width="80px">
        <el-form-item label="学生"><el-select v-model="dormForm.student_id" filterable><el-option v-for="s in allStudents" :key="s.id" :label="s.name" :value="s.id" /></el-select></el-form-item>
        <el-form-item label="宿舍号"><el-select v-model="dormForm.room_no" filterable allow-create><el-option v-for="r in dormRooms" :key="r.id" :label="r.room_no" :value="r.room_no" /></el-select></el-form-item>
      </el-form>
      <template #footer><el-button @click="dormDialog = false">取消</el-button><el-button type="primary" @click="saveDorm">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="roomDialog" title="添加宿舍" width="400px">
      <el-form label-width="80px">
        <el-form-item label="宿舍号"><el-input v-model="roomForm.room_no" /></el-form-item>
        <el-form-item label="容量"><el-input-number v-model="roomForm.capacity" :min="1" :max="12" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="roomDialog = false">取消</el-button><el-button type="primary" @click="saveRoom">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="dutyDialog" title="添加值日安排" width="520px">
      <el-form label-width="80px">
        <el-form-item label="星期">
          <el-select v-model="dutyForm.weekday">
            <el-option v-for="i in 7" :key="i" :label="weekdayLabel(i)" :value="i" />
          </el-select>
        </el-form-item>
        <el-form-item label="值日生">
          <el-select v-model="dutyForm.student_ids" multiple filterable style="width: 100%">
            <el-option v-for="s in allStudents" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="工作分配">
          <div v-for="sid in dutyForm.student_ids" :key="sid" style="display: flex; align-items: center; margin-bottom: 6px">
            <span style="width: 90px">{{ studentName(sid) }}</span>
            <el-select v-model="dutyForm.jobs[sid]" placeholder="选择工作" style="flex: 1">
              <el-option v-for="j in dutyJobs" :key="j" :label="j" :value="j" />
            </el-select>
          </div>
          <span v-if="!dutyForm.student_ids.length" style="color: #909399; font-size: 12px">请先选择值日生</span>
        </el-form-item>
        <el-form-item label="备注"><el-input v-model="dutyForm.note" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dutyDialog = false">取消</el-button><el-button type="primary" @click="saveDuty">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getStudents, getCadres, createCadre, getDormRooms, createDormRoom,
  getDormAssignments, createDormAssignment, getSeatPlan, saveSeatPlan, getDuty, createDuty,
} from '@/api'

const activeTab = ref('cadre')
const loading = ref(false)
const allStudents = ref<any[]>([])
const cadres = ref<any[]>([])
const dormRooms = ref<any[]>([])
const dormAssignments = ref<any[]>([])
const dutyList = ref<any[]>([])

const cadreDialog = ref(false)
const dormDialog = ref(false)
const roomDialog = ref(false)
const dutyDialog = ref(false)
const cadreForm = reactive<any>({})
const dormForm = reactive<any>({})
const roomForm = reactive<any>({ capacity: 4 })
const dutyForm = reactive<any>({ weekday: 1, student_ids: [], jobs: {} })
const dutyWeekdayFilter = ref<number | undefined>(undefined)
const dutyJobs = ['扫地', '拖地', '擦黑板', '整理讲台窗台', '刷地']

const seatRows = ref(6)
const seatCols = ref(8)
const seatGrid = ref<any[]>([])

const weekdayLabel = (i: number) => ['', '周一', '周二', '周三', '周四', '周五', '周六', '周日'][i]

const studentName = (sid: number) => {
  const s = allStudents.value.find((x: any) => x.id === sid)
  return s ? s.name : ''
}

const loadAll = async () => {
  loading.value = true
  try {
    const [students, c, r, a, duty, seat] = await Promise.all([
      getStudents({ page: 1, size: 200 }),
      getCadres(), getDormRooms(), getDormAssignments(), getDuty(), getSeatPlan(),
    ])
    allStudents.value = (students as any).data
    cadres.value = (c as any).data
    dormRooms.value = (r as any).data
    dormAssignments.value = (a as any).data
    dutyList.value = (duty as any).data
    if ((seat as any).data) {
      seatRows.value = (seat as any).data.rows
      seatCols.value = (seat as any).data.cols
      const layout = (seat as any).data.layout
      initSeatGrid(layout)
    } else {
      initSeatGrid()
    }
  } finally {
    loading.value = false
  }
}

const loadDuty = async () => {
  const params = dutyWeekdayFilter.value ? { weekday: dutyWeekdayFilter.value } : {}
  const res: any = await getDuty(params)
  dutyList.value = res.data
}

const initSeatGrid = (layout?: any) => {
  const total = seatRows.value * seatCols.value
  const arr: any[] = []
  for (let i = 0; i < total; i++) {
    arr.push({ studentId: layout ? (layout[i] ?? null) : null })
  }
  seatGrid.value = arr
}

const reassignSeat = (_i: number, sid: any) => {
  // 若同一学生已在其他座位，清空原座位
  if (sid) {
    seatGrid.value.forEach((c, idx) => {
      if (idx !== _i && c.studentId === sid) c.studentId = null
    })
  }
}

const saveSeat = async () => {
  const layout: any = {}
  seatGrid.value.forEach((c, i) => { layout[i] = c.studentId })
  await saveSeatPlan({ rows: seatRows.value, cols: seatCols.value, layout })
  ElMessage.success('座位表已保存')
}

const openCadreDialog = () => { Object.keys(cadreForm).forEach((k) => delete cadreForm[k]); cadreForm.start_date = new Date().toISOString().slice(0, 10); cadreDialog.value = true }
const saveCadre = async () => {
  if (!cadreForm.student_id || !cadreForm.position) { ElMessage.warning('请填写完整'); return }
  await createCadre(cadreForm); ElMessage.success('已登记'); cadreDialog.value = false; loadAll()
}
const openDormDialog = () => { Object.keys(dormForm).forEach((k) => delete dormForm[k]); dormForm.start_date = new Date().toISOString().slice(0, 10); dormDialog.value = true }
const saveDorm = async () => {
  if (!dormForm.student_id || !dormForm.room_no) { ElMessage.warning('请填写完整'); return }
  await createDormAssignment(dormForm); ElMessage.success('已分配'); dormDialog.value = false; loadAll()
}
const openRoomDialog = () => { roomForm.room_no = ''; roomForm.capacity = 4; roomDialog.value = true }
const saveRoom = async () => {
  if (!roomForm.room_no) { ElMessage.warning('请输入宿舍号'); return }
  await createDormRoom(roomForm); ElMessage.success('已添加'); roomDialog.value = false; loadAll()
}
const openDutyDialog = () => { dutyForm.weekday = 1; dutyForm.student_ids = []; dutyForm.jobs = {}; dutyForm.note = ''; dutyDialog.value = true }
const saveDuty = async () => {
  if (!dutyForm.student_ids.length) { ElMessage.warning('请选择值日生'); return }
  // jobs 键转为字符串
  const jobs: any = {}
  dutyForm.student_ids.forEach((sid: number) => { jobs[String(sid)] = dutyForm.jobs[sid] || '' })
  await createDuty({ weekday: dutyForm.weekday, student_ids: dutyForm.student_ids, jobs, note: dutyForm.note })
  ElMessage.success('已排班'); dutyDialog.value = false; loadDuty()
}

onMounted(loadAll)
</script>

<style scoped>
.seat-grid {
  display: grid;
  gap: 8px;
  margin-top: 8px;
}
.seat-cell {
  border: 1px dashed #dcdfe6;
  border-radius: 6px;
  padding: 6px;
}
</style>
