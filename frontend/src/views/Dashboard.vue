<template>
  <div class="page-container">
    <div class="stat-card-grid">
      <div class="stat-card">
        <div class="label">在册人数</div>
        <div class="value">{{ overview.total_students ?? '—' }}</div>
      </div>
      <div class="stat-card">
        <div class="label">今日出勤率</div>
        <div class="value">{{ rateText }}</div>
      </div>
      <div class="stat-card">
        <div class="label">本周旷课人次</div>
        <div class="value">{{ overview.week_absent ?? '—' }}</div>
      </div>
      <div class="stat-card">
        <div class="label">当前学期挂科人数</div>
        <div class="value">{{ overview.fail_students ?? '—' }}</div>
      </div>
    </div>

    <el-row :gutter="20">
      <el-col :span="14">
        <div class="chart-card">
          <h3>近 30 天出勤率趋势</h3>
          <div ref="trendRef" style="height: 320px"></div>
        </div>
      </el-col>
      <el-col :span="10">
        <div class="chart-card">
          <h3>成绩分布</h3>
          <div ref="distRef" style="height: 320px"></div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="20">
      <el-col :span="24">
        <div class="chart-card">
          <h3>旷课次数 Top 榜</h3>
          <el-table :data="rankings.absent_top" size="small" empty-text="暂无数据">
            <el-table-column type="index" label="#" width="50" />
            <el-table-column prop="name" label="姓名" />
            <el-table-column prop="count" label="旷课次数" width="100" />
          </el-table>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getOverview, getAttendanceTrend, getScoreDistribution, getRankings } from '@/api'

const overview = ref<any>({})
const rankings = ref<any>({ absent_top: [] })
const trendRef = ref()
const distRef = ref()

const rateText = computed(() =>
  overview.value.today_rate != null ? (overview.value.today_rate * 100).toFixed(1) + '%' : '—'
)

const renderTrend = (data: any[]) => {
  const chart = echarts.init(trendRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 20, top: 20, bottom: 40 },
    xAxis: { type: 'category', data: data.map((d) => d.date.slice(5)), boundaryGap: false },
    yAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' } },
    series: [
      {
        type: 'line',
        data: data.map((d) => d.rate),
        smooth: true,
        areaStyle: { opacity: 0.15 },
        itemStyle: { color: '#409EFF' },
        connectNulls: true,
      },
    ],
  })
  window.addEventListener('resize', () => chart.resize())
}

const renderDist = (data: any[]) => {
  const chart = echarts.init(distRef.value)
  chart.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [
      {
        type: 'pie',
        radius: ['40%', '65%'],
        data: data.map((d) => ({ name: d.name, value: d.value })),
        label: { formatter: '{b}: {c}' },
      },
    ],
  })
  window.addEventListener('resize', () => chart.resize())
}

onMounted(async () => {
  const [o, t, d, r] = await Promise.all([
    getOverview(),
    getAttendanceTrend({ days: 30 }),
    getScoreDistribution(),
    getRankings(),
  ])
  overview.value = (o as any).data
  rankings.value = (r as any).data
  await nextTick()
  renderTrend((t as any).data)
  renderDist((d as any).data)
})
</script>
