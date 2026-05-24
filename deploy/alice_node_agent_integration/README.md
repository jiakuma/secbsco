# Alice Node-Agent 集成说明

## 目标

在现有 Alice node-agent (19090) 中新增 `/services/start` 接口，用于自动启动 bio-task-runtime 18190。

## 现有 node-agent 信息

- 地址：http://123.60.109.244:19090
- 已有接口：
  - `POST /activate` - 激活节点
  - `POST /deactivate` - 停止节点
  - `GET /health` - 健康检查

## 集成步骤

### 1. 复制文件到 Alice 服务器

```bash
# 将 services_start_router.py 复制到 node-agent 项目目录
scp services_start_router.py root@123.60.109.244:/opt/node-agent/
```

### 2. 修改 node-agent 主程序

在现有 node-agent 主文件中添加：

```python
# 导入路由
from services_start_router import router as services_router

# 挂载路由
app.include_router(services_router)
```

### 3. 重启 node-agent

```bash
# 查找并停止现有进程
ps aux | grep node_agent
kill <PID>

# 重新启动
cd /opt/node-agent
nohup python -m uvicorn node_agent_main:app --host 0.0.0.0 --port 19090 > logs/node_agent.log 2>&1 &
```

### 4. 验证

```bash
# 测试新接口
curl -X POST http://123.60.109.244:19090/services/start \
  -H "Content-Type: application/json" \
  -d '{"service_code": "bio_task_runtime"}'

# 查看服务状态
curl http://123.60.109.244:19090/services
```

## 接口说明

### POST /services/start

请求：
```json
{
  "service_code": "bio_task_runtime"
}
```

成功响应（已运行）：
```json
{
  "success": true,
  "message": "bio-task-runtime 已在运行",
  "service_code": "bio_task_runtime",
  "port": 18190,
  "already_running": true
}
```

成功响应（新启动）：
```json
{
  "success": true,
  "message": "bio-task-runtime 启动成功",
  "service_code": "bio_task_runtime",
  "port": 18190,
  "already_running": false
}
```

失败响应：
```json
{
  "success": false,
  "message": "启动超时，请检查日志",
  "log_path": "/opt/bio-task-runtime/logs/bio_task_runtime_18190.log"
}
```

## 白名单机制

只允许以下 service_code：
- `bio_task_runtime` (端口 18190)

不接受任意 shell 命令，确保安全。

## 启动逻辑

1. 检查 18190 端口是否已监听
2. 如已监听，检查 `/health` 接口
3. 如未启动，执行启动命令
4. 等待 3 秒后轮询 `/health`（最多 5 次，每次间隔 2 秒）
5. 返回结果

## 注意事项

1. 不改动现有 `/activate`、`/deactivate` 逻辑
2. 不改动 Bob、Ray 启动逻辑
3. 仅新增最小化服务启动接口
