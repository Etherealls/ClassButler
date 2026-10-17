<template>
  <div class="page-container">
    <div class="stat-card-grid">
      <div class="stat-card">
        <div class="label">在册人数</div>
        <div class="value">{{ overview.total_students ?? '—' }}</div>
      </div>
      <div class="stat-card">
        <div class="label">学生干部</div>
        <div class="value">{{ overview.cadre_count ?? '—' }}</div>
      </div>
      <div class="stat-card">
        <div class="label">住宿人数</div>
        <div class="value">{{ overview.dorm_count ?? '—' }}</div>
      </div>
      <div class="stat-card">
        <div class="label">荣誉/证书数</div>
        <div class="value">{{ totalHonors }}</div>
      </div>
      <div class="stat-card">
        <div class="label">已评价人数</div>
        <div class="value">{{ overview.evaluated ?? '—' }}</div>
      </div>
      <div class="stat-card">
        <div class="label">待评价人数</div>
        <div class="value">{{ overview.unevaluated ?? '—' }}</div>
      </div>
    </div>

    <el-row :gutter="20">
      <el-col :span="14">
        <div class="chart-card">
          <h3>综合素质评价等级分布</h3>
          <div ref="distRef" style="height: 340px"></div>
        </div>
      </el-col>
      <el-col :span="10">
        <div class="chart-card">
          <h3>荣誉 Top 榜</h3>
          <el-table :data="honorTop" size="small" empty-text="暂无数据">
            <el-table-column type="index" label="#" width="50" />
            <el-table-column prop="name" label="姓名" />
            <el-table-column prop="count" label="荣誉/证书数" width="120" />
          </el-table>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getOverview, getQualityDistribution, getHonorTop } from '@/api'

const overview = ref<any>({})
const honorTop = ref<any[]>([])
const distRef = ref()

const totalHonors = computed(() =>
  (overview.value.award_count ?? 0) + (overview.value.cert_count ?? 0)
)

const renderDist = (data: any[]) => {
  const chart = echarts.init(distRef.value)
  chart.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    color: ['#67C23A', '#409EFF', '#E6A23C', '#F56C6C'],
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
  const [o, d, h] = await Promise.all([
    getOverview(),
    getQualityDistribution(),
    getHonorTop(),
  ])
  overview.value = (o as any).data
  honorTop.value = (h as any).data || []
  await nextTick()
  renderDist((d as any).data)
})
</script>
