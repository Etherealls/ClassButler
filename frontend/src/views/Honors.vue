<template>
  <div class="page-container">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="竞赛获奖" name="award">
        <div class="toolbar">
          <el-select v-model="awardLevel" placeholder="级别" clearable style="width: 120px" @change="loadAwards">
            <el-option v-for="l in levels" :key="l" :label="l" :value="l" />
          </el-select>
          <div class="spacer"></div>
          <el-button type="primary" @click="openAwardDialog">登记获奖</el-button>
        </div>
        <el-table :data="awards" border stripe v-loading="loading">
          <el-table-column prop="student_no" label="学号" width="100" />
          <el-table-column prop="student_name" label="姓名" width="100" />
          <el-table-column prop="event_name" label="赛事名称" />
          <el-table-column prop="level" label="级别" width="80" />
          <el-table-column prop="award" label="奖项" width="100" />
          <el-table-column prop="award_time" label="获奖时间" width="120" />
          <el-table-column prop="cert_no" label="证书编号" />
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="职业证书" name="cert">
        <div class="toolbar">
          <div class="spacer"></div>
          <el-button type="primary" @click="openCertDialog">登记证书</el-button>
        </div>
        <el-table :data="certs" border stripe v-loading="loading">
          <el-table-column prop="student_no" label="学号" width="100" />
          <el-table-column prop="student_name" label="姓名" width="100" />
          <el-table-column prop="cert_name" label="证书名称" />
          <el-table-column prop="grade" label="等级" width="100" />
          <el-table-column prop="obtain_time" label="取得时间" width="120" />
          <el-table-column prop="cert_no" label="编号" />
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="awardDialog" title="登记获奖" width="500px">
      <el-form :model="awardForm" label-width="90px">
        <el-form-item label="学生" required><el-select v-model="awardForm.student_id" filterable style="width: 100%"><el-option v-for="s in students" :key="s.id" :label="`${s.name}（${s.student_no}）`" :value="s.id" /></el-select></el-form-item>
        <el-form-item label="赛事名称" required><el-input v-model="awardForm.event_name" /></el-form-item>
        <el-form-item label="级别" required><el-select v-model="awardForm.level" style="width: 100%"><el-option v-for="l in levels" :key="l" :label="l" :value="l" /></el-select></el-form-item>
        <el-form-item label="奖项" required><el-input v-model="awardForm.award" /></el-form-item>
        <el-form-item label="获奖时间"><el-date-picker v-model="awardForm.award_time" type="date" value-format="YYYY-MM-DD" style="width: 100%" /></el-form-item>
        <el-form-item label="证书编号"><el-input v-model="awardForm.cert_no" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="awardDialog = false">取消</el-button><el-button type="primary" @click="saveAward">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="certDialog" title="登记证书" width="500px">
      <el-form :model="certForm" label-width="90px">
        <el-form-item label="学生" required><el-select v-model="certForm.student_id" filterable style="width: 100%"><el-option v-for="s in students" :key="s.id" :label="`${s.name}（${s.student_no}）`" :value="s.id" /></el-select></el-form-item>
        <el-form-item label="证书名称" required><el-input v-model="certForm.cert_name" /></el-form-item>
        <el-form-item label="等级"><el-input v-model="certForm.grade" /></el-form-item>
        <el-form-item label="取得时间"><el-date-picker v-model="certForm.obtain_time" type="date" value-format="YYYY-MM-DD" style="width: 100%" /></el-form-item>
        <el-form-item label="编号"><el-input v-model="certForm.cert_no" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="certDialog = false">取消</el-button><el-button type="primary" @click="saveCert">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getStudents, getAwards, createAward, getCertificates, createCertificate } from '@/api'

const levels = ['校', '市', '省', '国家', '国际']
const activeTab = ref('award')
const loading = ref(false)
const students = ref<any[]>([])
const awards = ref<any[]>([])
const certs = ref<any[]>([])
const awardLevel = ref('')
const awardDialog = ref(false)
const certDialog = ref(false)
const awardForm = reactive<any>({})
const certForm = reactive<any>({})

const loadAwards = async () => {
  loading.value = true
  try {
    const res: any = await getAwards({ level: awardLevel.value || undefined })
    awards.value = res.data
  } finally { loading.value = false }
}

const loadCerts = async () => {
  loading.value = true
  try {
    const res: any = await getCertificates({})
    certs.value = res.data
  } finally { loading.value = false }
}

const openAwardDialog = () => { Object.keys(awardForm).forEach((k) => delete awardForm[k]); awardDialog.value = true }
const saveAward = async () => {
  if (!awardForm.student_id || !awardForm.event_name || !awardForm.level || !awardForm.award) { ElMessage.warning('请填写完整'); return }
  await createAward(awardForm); ElMessage.success('已登记'); awardDialog.value = false; loadAwards()
}
const openCertDialog = () => { Object.keys(certForm).forEach((k) => delete certForm[k]); certDialog.value = true }
const saveCert = async () => {
  if (!certForm.student_id || !certForm.cert_name) { ElMessage.warning('请填写完整'); return }
  await createCertificate(certForm); ElMessage.success('已登记'); certDialog.value = false; loadCerts()
}

onMounted(async () => {
  loadAwards(); loadCerts()
  const res: any = await getStudents({ page: 1, size: 200 })
  students.value = res.data
})
</script>
