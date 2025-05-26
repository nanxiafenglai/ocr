# 验证码识别系统 - 架构升级计划

## 📐 架构概述

本文档详细描述了验证码识别系统从单体架构向微服务架构的升级计划，包括技术选型、迁移策略、部署方案等。

## 🏗️ 当前架构分析

### 现有架构
```
┌─────────────────────────────────────┐
│           单体应用                    │
├─────────────────────────────────────┤
│  Flask API + 命令行工具              │
│  ├── captcha_recognizer/            │
│  │   ├── recognizer.py             │
│  │   ├── processors/               │
│  │   └── utils/                    │
│  ├── flask_api.py                  │
│  └── main.py                       │
└─────────────────────────────────────┘
```

### 架构优势
- 部署简单，易于开发和调试
- 代码结构清晰，模块化设计良好
- 适合小规模应用和快速原型

### 架构限制
- 单点故障风险
- 扩展性受限
- 技术栈绑定
- 资源利用率不高

## 🎯 目标架构设计

### 微服务架构图
```
                    ┌─────────────────┐
                    │   API Gateway   │
                    │   (Kong/Nginx)  │
                    └─────────┬───────┘
                              │
            ┌─────────────────┼─────────────────┐
            │                 │                 │
    ┌───────▼──────┐ ┌────────▼────────┐ ┌─────▼─────┐
    │ Auth Service │ │ Recognition API │ │ Management│
    │   (FastAPI)  │ │   (FastAPI)     │ │   Portal  │
    └──────────────┘ └─────────────────┘ └───────────┘
                              │
                    ┌─────────┼─────────┐
                    │         │         │
            ┌───────▼──┐ ┌────▼────┐ ┌──▼──────┐
            │Image Proc│ │OCR Engine│ │Cache Svc│
            │ Service  │ │ Service  │ │(Redis)  │
            └──────────┘ └─────────┘ └─────────┘
                              │
                    ┌─────────┼─────────┐
                    │         │         │
            ┌───────▼──┐ ┌────▼────┐ ┌──▼──────┐
            │Database  │ │Message Q│ │Monitoring│
            │(PostgreSQL)│ │(Redis) │ │(Prometheus)│
            └──────────┘ └─────────┘ └─────────┘
```

### 服务职责划分

#### 1. API Gateway (Kong/Nginx)
- **职责**: 请求路由、负载均衡、认证、限流
- **技术栈**: Kong + Lua 或 Nginx + OpenResty
- **端口**: 80/443

#### 2. Authentication Service
- **职责**: 用户认证、API密钥管理、权限控制
- **技术栈**: FastAPI + JWT + PostgreSQL
- **端口**: 8001

#### 3. Recognition API Service
- **职责**: 验证码识别API、请求分发、结果聚合
- **技术栈**: FastAPI + Celery
- **端口**: 8002

#### 4. Image Processing Service
- **职责**: 图像预处理、格式转换、质量优化
- **技术栈**: FastAPI + OpenCV + PIL
- **端口**: 8003

#### 5. OCR Engine Service
- **职责**: 核心识别逻辑、模型管理、结果后处理
- **技术栈**: FastAPI + ddddocr + PyTorch
- **端口**: 8004

#### 6. Cache Service
- **职责**: 缓存管理、会话存储、临时数据
- **技术栈**: Redis Cluster
- **端口**: 6379

#### 7. Management Portal
- **职责**: Web管理界面、监控面板、配置管理
- **技术栈**: Vue.js + Element UI
- **端口**: 8080

## 🔄 迁移策略

### 阶段一：基础设施准备（1-2周）

#### 1.1 容器化改造
```dockerfile
# Dockerfile示例
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 1.2 Docker Compose配置
```yaml
version: '3.8'
services:
  api-gateway:
    image: kong:latest
    ports:
      - "80:8000"
      - "443:8443"
    environment:
      KONG_DATABASE: "off"
      KONG_DECLARATIVE_CONFIG: "/kong/declarative/kong.yml"
    volumes:
      - ./kong.yml:/kong/declarative/kong.yml

  auth-service:
    build: ./services/auth
    ports:
      - "8001:8000"
    environment:
      DATABASE_URL: postgresql://user:pass@postgres:5432/auth_db
    depends_on:
      - postgres

  recognition-api:
    build: ./services/recognition
    ports:
      - "8002:8000"
    environment:
      REDIS_URL: redis://redis:6379
    depends_on:
      - redis
      - postgres

  postgres:
    image: postgres:13
    environment:
      POSTGRES_DB: captcha_db
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:6-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

### 阶段二：服务拆分（2-3周）

#### 2.1 认证服务实现
```python
# services/auth/main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer
import jwt

app = FastAPI(title="Authentication Service")
security = HTTPBearer()

@app.post("/auth/login")
async def login(credentials: UserCredentials):
    # 验证用户凭据
    if verify_credentials(credentials):
        token = generate_jwt_token(credentials.username)
        return {"access_token": token, "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/auth/verify")
async def verify_token(token: str = Depends(security)):
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=["HS256"])
        return {"valid": True, "user": payload["sub"]}
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

#### 2.2 识别API服务
```python
# services/recognition/main.py
from fastapi import FastAPI, BackgroundTasks
from celery import Celery

app = FastAPI(title="Recognition API Service")
celery_app = Celery('recognition', broker='redis://redis:6379')

@app.post("/recognize")
async def recognize_captcha(
    request: RecognitionRequest,
    background_tasks: BackgroundTasks
):
    # 异步处理识别任务
    task = celery_app.send_task(
        'recognition.process_captcha',
        args=[request.image_data, request.captcha_type]
    )
    
    return {
        "task_id": task.id,
        "status": "processing",
        "estimated_time": 5
    }

@app.get("/recognize/{task_id}")
async def get_recognition_result(task_id: str):
    task = celery_app.AsyncResult(task_id)
    
    if task.ready():
        return {
            "task_id": task_id,
            "status": "completed",
            "result": task.result
        }
    else:
        return {
            "task_id": task_id,
            "status": "processing"
        }
```

### 阶段三：数据层改造（1-2周）

#### 3.1 数据库设计
```sql
-- 用户服务数据库
CREATE DATABASE auth_db;

-- 用户表
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    api_key VARCHAR(64) UNIQUE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- API密钥表
CREATE TABLE api_keys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    key_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100),
    permissions JSONB,
    rate_limit INTEGER DEFAULT 1000,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 识别服务数据库
CREATE DATABASE recognition_db;

-- 识别历史表
CREATE TABLE recognition_history (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    task_id VARCHAR(64) UNIQUE,
    image_hash VARCHAR(64),
    captcha_type VARCHAR(20),
    result TEXT,
    confidence FLOAT,
    processing_time FLOAT,
    status VARCHAR(20),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- 索引优化
CREATE INDEX idx_user_created ON recognition_history(user_id, created_at);
CREATE INDEX idx_task_id ON recognition_history(task_id);
CREATE INDEX idx_image_hash ON recognition_history(image_hash);
```

#### 3.2 数据迁移脚本
```python
# migration/migrate_data.py
import asyncio
import asyncpg
from sqlalchemy import create_engine

async def migrate_users():
    # 从旧系统迁移用户数据
    old_conn = create_engine('sqlite:///old_db.sqlite')
    new_conn = await asyncpg.connect('postgresql://user:pass@localhost/auth_db')
    
    # 迁移逻辑
    pass

async def migrate_history():
    # 迁移识别历史数据
    pass
```

### 阶段四：监控和运维（1周）

#### 4.1 Kubernetes部署配置
```yaml
# k8s/recognition-api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: recognition-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: recognition-api
  template:
    metadata:
      labels:
        app: recognition-api
    spec:
      containers:
      - name: recognition-api
        image: captcha-recognizer/recognition-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
        - name: REDIS_URL
          value: "redis://redis-service:6379"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: recognition-api-service
spec:
  selector:
    app: recognition-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: ClusterIP
```

#### 4.2 监控配置
```yaml
# monitoring/prometheus-config.yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'recognition-api'
    static_configs:
      - targets: ['recognition-api-service:80']
    metrics_path: '/metrics'
    scrape_interval: 5s

  - job_name: 'auth-service'
    static_configs:
      - targets: ['auth-service:80']
    metrics_path: '/metrics'
    scrape_interval: 5s

rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

## 🚀 部署方案

### 开发环境
```bash
# 本地开发环境启动
docker-compose -f docker-compose.dev.yml up -d

# 服务健康检查
curl http://localhost:8001/health  # Auth Service
curl http://localhost:8002/health  # Recognition API
curl http://localhost:8003/health  # Image Processing
```

### 测试环境
```bash
# 测试环境部署
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmaps/
kubectl apply -f k8s/secrets/
kubectl apply -f k8s/deployments/
kubectl apply -f k8s/services/
kubectl apply -f k8s/ingress/
```

### 生产环境
```bash
# 生产环境部署
helm install captcha-recognizer ./helm-chart \
  --namespace production \
  --values values.prod.yaml

# 监控部署
helm install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --values monitoring-values.yaml
```

## 📊 性能对比

### 预期性能提升

| 指标 | 单体架构 | 微服务架构 | 提升比例 |
|------|----------|------------|----------|
| 并发处理能力 | 100 QPS | 1000+ QPS | 10x |
| 响应时间 | 1000ms | 300ms | 70% |
| 可用性 | 99% | 99.9% | 0.9% |
| 扩展性 | 垂直扩展 | 水平扩展 | 无限 |

### 资源利用率

| 资源 | 单体架构 | 微服务架构 | 优化效果 |
|------|----------|------------|----------|
| CPU利用率 | 30% | 70% | +40% |
| 内存利用率 | 40% | 80% | +40% |
| 网络带宽 | 50% | 85% | +35% |

## 🎯 迁移检查清单

### 基础设施
- [ ] Docker镜像构建
- [ ] Docker Compose配置
- [ ] Kubernetes集群准备
- [ ] 网络配置
- [ ] 存储配置

### 服务开发
- [ ] 认证服务开发
- [ ] 识别API服务开发
- [ ] 图像处理服务开发
- [ ] OCR引擎服务开发
- [ ] 缓存服务配置

### 数据迁移
- [ ] 数据库设计
- [ ] 数据迁移脚本
- [ ] 数据验证
- [ ] 备份策略

### 监控运维
- [ ] Prometheus配置
- [ ] Grafana面板
- [ ] 告警规则
- [ ] 日志聚合
- [ ] 健康检查

### 测试验证
- [ ] 单元测试
- [ ] 集成测试
- [ ] 性能测试
- [ ] 压力测试
- [ ] 安全测试

## 🚨 风险评估

### 技术风险
- **服务间通信复杂性**: 使用服务网格(Istio)简化
- **数据一致性**: 实现分布式事务或最终一致性
- **网络延迟**: 优化服务间调用，使用缓存

### 运维风险
- **部署复杂性**: 使用Helm简化部署
- **监控盲点**: 完善监控体系
- **故障排查**: 实现分布式链路追踪

### 业务风险
- **服务中断**: 实现灰度发布和回滚机制
- **性能下降**: 充分的性能测试和优化
- **数据丢失**: 完善的备份和恢复策略

---

*本架构升级计划提供了详细的迁移路径，建议分阶段实施，确保系统稳定性。*
