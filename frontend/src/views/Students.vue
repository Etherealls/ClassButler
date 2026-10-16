<template>
  <div class="page-container">
    <div class="toolbar">
      <el-input v-model="keyword" placeholder="姓名/学号搜索" clearable style="width: 220px" @input="load" />
      <el-select v-model="gender" placeholder="性别" clearable style="width: 120px" @change="load">
        <el-option label="男" value="男" />
        <el-option label="女" value="女" />
      </el-select>
      <el-button type="primary" @click="load">查询</el-button>
      <div class="spacer"></div>
      <el-button @click="downloadTemplate">下载模板</el-button>
      <el-upload :show-file-list="false" :before-upload="handleImport" accept=".xlsx">
        <el-button>批量导入</el-button>
      </el-upload>
      <el-button @click="handleExport">导出花名册</el-button>
      <el-button type="success" @click="openDialog()">新增学生</el-button>
    </div>

    <el-table :data="list" border stripe v-loading="loading">
      <el-table-column prop="student_no" label="学号" width="100" />
      <el-table-column prop="name" label="姓名" width="100" />
      <el-table-column prop="gender" label="性别" width="60" />
      <el-table-column prop="birth_date" label="出生日期" width="110" />
      <el-table-column prop="nation" label="民族" width="70" />
      <el-table-column prop="native_place" label="籍贯" />
      <el-table-column prop="origin" label="生源地" />
      <el-table-column prop="phone" label="手机号" width="130" />
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
          <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      class="pagination"
      :current-page="page"
      :page-size="size"
      :total="total"
      layout="total, prev, pager, next"
      @current-change="(p: number) => { page = p; load() }"
    />

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑学生' : '新增学生'" width="720px">
      <el-form :model="form" label-width="100px">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="学号" required><el-input v-model="form.student_no" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="姓名" required><el-input v-model="form.name" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="性别" required>
              <el-radio-group v-model="form.gender">
                <el-radio label="男">男</el-radio>
                <el-radio label="女">女</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="出生日期">
              <el-date-picker v-model="form.birth_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="身份证号"><el-input v-model="form.id_card" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="民族"><el-input v-model="form.nation" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="政治面貌"><el-input v-model="form.political" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="籍贯"><el-input v-model="form.native_place" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="生源地"><el-input v-model="form.origin" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="手机号"><el-input v-model="form.phone" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="家庭住址"><el-input v-model="form.address" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="紧急联系人"><el-input v-model="form.emergency_name" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="紧急电话"><el-input v-model="form.emergency_phone" /></el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="家庭备注"><el-input v-model="form.family_note" type="textarea" /></el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getStudents, createStudent, updateStudent, deleteStudent, importStudents, exportStudents,
} from '@/api'
import request from '@/api/request'

const list = ref<any[]>([])
const loading = ref(false)
const keyword = ref('')
const gender = ref('')
const page = ref(1)
const size = ref(20)
const total = ref(0)
const dialogVisible = ref(false)
const form = reactive<any>({})

const load = async () => {
  loading.value = true
  try {
    const res: any = await getStudents({ keyword: keyword.value, gender: gender.value, page: page.value, size: size.value })
    list.value = res.data
    total.value = res.total
  } finally {
    loading.value = false
  }
}

const openDialog = (row?: any) => {
  Object.keys(form).forEach((k) => delete form[k])
  if (row) {
    Object.assign(form, row)
    form.id = row.id
  } else {
    form.gender = '男'
  }
  dialogVisible.value = true
}

const handleSave = async () => {
  if (!form.student_no || !form.name || !form.gender) {
    ElMessage.warning('学号/姓名/性别为必填')
    return
  }
  if (form.id) {
    await updateStudent(form.id, { ...form, id: undefined })
    ElMessage.success('更新成功')
  } else {
    await createStudent(form)
    ElMessage.success('建档成功')
  }
  dialogVisible.value = false
  load()
}

const handleDelete = (row: any) => {
  ElMessageBox.confirm(`确定删除学生「${row.name}」吗？`, '提示', { type: 'warning' }).then(async () => {
    await deleteStudent(row.id)
    ElMessage.success('已删除')
    load()
  })
}

const downloadTemplate = async () => {
  const res: any = await request.get('/students/template', { responseType: 'blob' })
  saveBlob(res.data, 'students_template.xlsx')
}

const handleImport = async (file: File) => {
  const fd = new FormData()
  fd.append('file', file)
  const res: any = await importStudents(fd)
  const { success, errors } = res.data
  if (errors && errors.length) {
    ElMessage.warning(`成功 ${success} 条，失败 ${errors.length} 条：${errors.slice(0, 3).map((e: any) => `第${e.row}行 ${e.reason}`).join('；')}`)
  } else {
    ElMessage.success(`成功导入 ${success} 条`)
  }
  load()
  return false
}

const handleExport = async () => {
  const res: any = await exportStudents({})
  saveBlob(res.data, 'roster.xlsx')
}

const saveBlob = (blob: Blob, filename: string) => {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

onMounted(load)
</script>

<style scoped>
.pagination {
  margin-top: 16px;
  justify-content: flex-end;
}
</style>
