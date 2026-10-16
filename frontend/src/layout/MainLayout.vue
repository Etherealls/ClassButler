<template>
  <el-container class="layout">
    <el-aside width="220px" class="aside">
      <div class="logo">
        <el-icon><School /></el-icon>
        <span>班主任管理系统</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        background-color="#001529"
        text-color="#a6adb4"
        active-text-color="#ffffff"
        class="menu"
      >
        <el-menu-item index="/dashboard">
          <el-icon><DataLine /></el-icon><span>数据看板</span>
        </el-menu-item>
        <el-menu-item index="/students">
          <el-icon><User /></el-icon><span>学生档案</span>
        </el-menu-item>
        <el-menu-item index="/organization">
          <el-icon><OfficeBuilding /></el-icon><span>班级组织</span>
        </el-menu-item>
        <el-menu-item index="/attendance">
          <el-icon><Calendar /></el-icon><span>考勤管理</span>
        </el-menu-item>
        <el-menu-item index="/leaves">
          <el-icon><Document /></el-icon><span>请假登记</span>
        </el-menu-item>
        <el-menu-item index="/dorm-check">
          <el-icon><Moon /></el-icon><span>查寝管理</span>
        </el-menu-item>
        <el-menu-item index="/discipline">
          <el-icon><Warning /></el-icon><span>纪律记录</span>
        </el-menu-item>
        <el-menu-item index="/scores">
          <el-icon><Histogram /></el-icon><span>成绩管理</span>
        </el-menu-item>
        <el-menu-item index="/alerts">
          <el-icon><Bell /></el-icon><span>学业预警</span>
        </el-menu-item>
        <el-menu-item index="/makeup">
          <el-icon><RefreshRight /></el-icon><span>补考重修</span>
        </el-menu-item>
        <el-menu-item index="/honors">
          <el-icon><Trophy /></el-icon><span>荣誉证书</span>
        </el-menu-item>
        <el-menu-item index="/account">
          <el-icon><Setting /></el-icon><span>账号设置</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-title">{{ currentTitle }}</div>
        <div class="header-right">
          <span class="username">{{ userStore.username }}（班主任）</span>
          <el-button link type="danger" @click="handleLogout">退出登录</el-button>
        </div>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useUserStore } from '@/store/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const activeMenu = computed(() => route.path)
const currentTitle = computed(() => (route.meta.title as string) || '数据看板')

const handleLogout = () => {
  ElMessageBox.confirm('确定退出登录吗？', '提示', { type: 'warning' }).then(() => {
    userStore.logout()
    router.push('/login')
  })
}
</script>

<style scoped>
.layout {
  height: 100%;
}
.aside {
  background: #001529;
}
.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}
.menu {
  border-right: none;
}
.header {
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
}
.header-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.username {
  color: #606266;
  font-size: 14px;
}
.main {
  padding: 0;
  overflow-y: auto;
}
</style>
