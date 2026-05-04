from pathlib import Path

# 前端项目根目录
BASE_DIR = Path(r"E:\py_project\PrimiHub\frontend")

# 需要创建的目录
DIRS = [
    "src/api",
    "src/router",
    "src/stores",
    "src/views",
]

# 需要创建的文件及默认内容
FILES = {
    ".env.development": """VITE_API_BASE_URL=http://127.0.0.1:8000
""",

    "src/api/request.ts": """// Axios 请求封装
""",

    "src/api/auth.ts": """// 登录认证相关接口
""",

    "src/router/index.ts": """// Vue Router 路由配置
""",

    "src/stores/auth.ts": """// Pinia 登录状态管理
""",

    "src/views/LoginView.vue": """<template>
  <div>
    登录页
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
</style>
""",

    "src/views/DashboardView.vue": """<template>
  <div>
    首页总览
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
</style>
""",

    "src/App.vue": """<template>
  <router-view />
</template>
""",

    "src/main.ts": """import { createApp } from 'vue'
import App from './App.vue'

createApp(App).mount('#app')
""",

    "src/style.css": """* {
  box-sizing: border-box;
}

body {
  margin: 0;
}
""",
}


def main():
    if not BASE_DIR.exists():
        print(f"前端目录不存在，正在创建：{BASE_DIR}")
        BASE_DIR.mkdir(parents=True, exist_ok=True)

    print("开始创建目录...")

    for dir_path in DIRS:
        full_path = BASE_DIR / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        print(f"目录已存在或创建成功：{full_path}")

    print("\n开始创建文件...")

    for file_path, content in FILES.items():
        full_path = BASE_DIR / file_path

        if full_path.exists():
            print(f"跳过已存在文件：{full_path}")
            continue

        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        print(f"文件创建成功：{full_path}")

    print("\n前端目录和文件创建完成。")


if __name__ == "__main__":
    main()