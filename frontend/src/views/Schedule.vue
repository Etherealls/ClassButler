<template>
  <div class="page-container">
    <el-tabs v-model="activeTab">
      <!-- ============ 课程表 ============ -->
      <el-tab-pane label="课程表" name="class">
        <schedule-table type="class" :semester="currentSemester" show-type-select />
      </el-tab-pane>

      <!-- ============ 实训课程表 ============ -->
      <el-tab-pane label="实训课程表" name="training">
        <schedule-table type="training" :semester="currentSemester" />
      </el-tab-pane>

      <!-- ============ 校历 ============ -->
      <el-tab-pane label="校历" name="calendar">
        <calendar-view :semester="currentSemester" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getSemesters } from '@/api'
import ScheduleTable from '@/components/ScheduleTable.vue'
import CalendarView from '@/components/CalendarView.vue'

const activeTab = ref('class')
const currentSemester = ref('')

onMounted(async () => {
  const res: any = await getSemesters()
  currentSemester.value = res.data.editable_semester || res.data.current_semester || ''
})
</script>
