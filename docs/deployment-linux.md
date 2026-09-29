# Octop Linux 生产环境部署手册

> 版本：v1.0.2b3 | 最后更新：2026-09-28

---

## 目录

1. [部署概述](#1-部署概述)
2. [系统要求](#2-系统要求)
3. [Docker 部署 (推荐)](#3-docker-部署-推荐)
4. [裸机部署](#4-裸机部署)
5. [PostgreSQL 配置](#5-postgresql-配置)
6. [配置详解](#6-配置详解)
7. [TLS/SSL 证书](#7-tlsssl-证书)
8. [系统服务 (systemd)](#8-系统服务-systemd)
9. [反向代理 (Nginx)](#9-反向代理-nginx)
10. [备份与恢复](#10-备份与恢复)
11. [监控与日志](#11-监控与日志)
12. [安全加固](#12-安全加固)
13. [性能调优](#13-性能调优)
14. [升级指南](#14-升级指南)
15. [故障排查](#15-故障排查)
16. [运维命令速查](#16-运维命令速查)

---

## 1. 部署概述

### 1.1 架构概览

```
                    ┌─────────────────────────────────────────┐
                    │              Octop 服务器                │
                    │                                         │
  用户 ──HTTPS──►   │  Nginx (可选) ──► uvicorn (FastAPI)     │
                    │                      │                  │
                    │              ┌───────┴───────┐          │
                    │              │  OctopServer   │          │
                    │              │  (单进程)      │          │
                    │              ├───────────────┤          │
                    │              │ AgentManager  │          │
                    │              │ Gateway       │          │
                    │              │ CronManager   │          │
                    │              │ UserManager   │          │
                    │              └───────┬───────┘          │
                    │                      │                  │
                    │              ┌───────┴───────┐          │
                    │              │  SQLite/PG    │          │
                    │              │  文件系统      │          │
                    │              └───────────────┘          │
                    └─────────────────────────────────────────┘
```

### 1.2 部署方式选择

| 方式 | 适用场景 | 优点 | 缺点 |
|------|---------|------|------|
| **Docker Compose** | 生产推荐 | 隔离、可复现、易升级 | 需要 Docker 知识 |
| **裸机 + systemd** | 资源受限、深度定制 | 直接访问硬件、低开销 | 需要手动管理依赖 |
| **Docker + PostgreSQL** | 多用户、高并发 | 数据库独立管理、易备份 | 组件更多 |

### 1.3 端口规划

| 端口 | 服务 | 说明 |
|------|------|------|
| 8088 | Octop HTTP | 默认监听端口 |
| 443 | HTTPS | TLS 启用后 (Octop 内置或 Nginx) |
| 80 | HTTP | ACME 证书验证 / 重定向到 HTTPS |
| 5432 | PostgreSQL | 仅本地监听 (不暴露) |

---

## 2. 系统要求

### 2.1 硬件要求

| 规模 | CPU | 内存 | 磁盘 | 说明 |
|------|-----|------|------|------|
| 小型 (1-10 用户) | 2 核 | 4 GB | 40 GB | SQLite 足够 |
| 中型 (10-100 用户) | 4 核 | 8 GB | 100 GB | 推荐 PostgreSQL |
| 大型 (100+ 用户) | 8+ 核 | 16+ GB | 500+ GB | PostgreSQL + 对象存储 |

### 2.2 软件要求

**Docker 部署：**

- Docker Engine >= 20.10
- Docker Compose >= 2.0
- 至少 10 GB 可用磁盘 (镜像 + 数据)

**裸机部署：**

- Linux 发行版：Ubuntu 22.04+, Debian 12+, RHEL 9+, CentOS Stream 9+
- Python >= 3.12
- Node.js >= 18 (仅构建时需要)
- Git >= 2.30

### 2.3 网络要求

| 目标 | 端口 | 用途 |
|------|------|------|
| LLM API (OpenAI, etc.) | 443 | Agent 对话 |
| PyPI (pypi.org) | 443 | 包升级 |
| Docker Hub | 443 | 镜像拉取 |
| Let's Encrypt | 80, 443 | TLS 证书 (可选) |
| IM 平台 Webhook | 443 | 钉钉/飞书等回调 |

---

## 3. Docker 部署 (推荐)

### 3.1 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/TencentCloud/Octop.git
cd Octop

# 2. 创建数据目录
mkdir -p ~/.octop

# 3. 配置环境变量
cp .env.example .env
vim .env
```

**最小 `.env` 配置：**

```bash
# 管理员凭据 (首次启动时使用)
OCTOP_ADMIN_USERNAME=admin
OCTOP_ADMIN_PASSWORD=YourStrongPassword123

# LLM 提供商 (至少配置一个)
OPENAI_API_KEY=sk-...
# 或
DASHSCOPE_API_KEY=sk-...

# 服务端口
OCTOP_PORT=8088

# 日志级别
OCTOP_LOG_LEVEL=info
```

```bash
# 4. 启动服务
cd docker
docker compose up -d

# 5. 查看日志
docker compose logs -f

# 6. 获取初始凭据 (如果未设置 OCTOP_ADMIN_PASSWORD)
docker compose exec octop cat /data/.octop/credential.txt
```

### 3.2 Docker Compose 配置

**基础配置 (`docker-compose.yml`)：**

```yaml
services:
  octop:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    container_name: octop
    restart: unless-stopped
    ports:
      - "${OCTOP_PORT:-8088}:${OCTOP_PORT:-8088}"
    volumes:
      - ${OCTOP_DATA:-~/.octop}:/data/.octop
    environment:
      - OCTOP_BIND_HOST=0.0.0.0
      - OCTOP_PORT=${OCTOP_PORT:-8088}
      - OCTOP_LOG_LEVEL=${OCTOP_LOG_LEVEL:-info}
      - OCTOP_ADMIN_USERNAME=${OCTOP_ADMIN_USERNAME:-}
      - OCTOP_ADMIN_PASSWORD=${OCTOP_ADMIN_PASSWORD:-}
      - OPENAI_API_KEY=${OPENAI_API_KEY:-}
      - DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY:-}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8088/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 90s
```

**带 PostgreSQL 的配置：**

```yaml
# docker-compose.prod.yml
services:
  octop:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    container_name: octop
    restart: unless-stopped
    ports:
      - "8088:8088"
    volumes:
      - octop_data:/data/.octop
    environment:
      - OCTOP_BIND_HOST=0.0.0.0
      - OCTOP_PORT=8088
      - OCTOP_LOG_LEVEL=info
      - OCTOP_DATABASE_DRIVER=postgresql
      - OCTOP_DATABASE_HOST=postgres
      - OCTOP_DATABASE_PORT=5432
      - OCTOP_DATABASE_NAME=octop
      - OCTOP_DATABASE_USER=octop
      - OCTOP_DATABASE_PASSWORD=${PG_PASSWORD}
      - OCTOP_ADMIN_USERNAME=${OCTOP_ADMIN_USERNAME}
      - OCTOP_ADMIN_PASSWORD=${OCTOP_ADMIN_PASSWORD}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8088/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 120s

  postgres:
    image: pgvector/pgvector:pg16
    container_name: octop-postgres
    restart: unless-stopped
    volumes:
      - pg_data:/var/lib/postgresql/data
      - ./postgres/init-vector.sql:/docker-entrypoint-initdb.d/init.sql
    environment:
      - POSTGRES_DB=octop
      - POSTGRES_USER=octop
      - POSTGRES_PASSWORD=${PG_PASSWORD}
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U octop"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  octop_data:
  pg_data:
```

### 3.3 国内镜像加速

```bash
# .env 中添加
PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
PIP_TRUSTED_HOST=mirrors.aliyun.com

# Dockerfile 构建参数
# docker build --build-arg PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ ...
# 或 docker compose build --build-arg PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
```

### 3.4 Docker 运维

```bash
# 启动/停止/重启
docker compose up -d
docker compose down
docker compose restart

# 查看日志
docker compose logs -f octop
docker compose logs --tail 100 octop

# 进入容器
docker compose exec octop bash

# 执行 CLI 命令
docker compose exec octop octop user list
docker compose exec octop octop agent list
docker compose exec octop octop backup create

# 查看资源使用
docker stats octop

# 更新镜像
docker compose pull
docker compose up -d --build
```

### 3.5 数据持久化

| 路径 | 说明 |
|------|------|
| `/data/.octop/config.json` | 主配置文件 |
| `/data/.octop/env` | 环境变量文件 |
| `/data/.octop/octop.db` | SQLite 数据库 (如使用 SQLite) |
| `/data/.octop/secrets/` | 加密密钥 |
| `/data/.octop/agents/` | Agent 工作空间 |
| `/data/.octop/plugins/` | 插件 |
| `/data/.octop/skill_packages/` | 技能包 |
| `/data/.octop/logs/` | 日志文件 |
| `/data/.octop/ssl/` | TLS 证书 |

**备份关键数据：**

```bash
# 备份整个数据目录
docker compose exec octop octop backup create

# 或手动复制
docker run --rm -v octop_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/octop-backup-$(date +%Y%m%d).tar.gz /data
```

---

## 4. 裸机部署

### 4.1 安装依赖

**Ubuntu/Debian：**

```bash
# 系统依赖
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3-pip \
    git curl build-essential libffi-dev libssl-dev

# 安装 uv (Python 包管理器)
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env

# 安装 Node.js (仅构建前端时需要)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# 验证版本
python3.12 --version  # >= 3.12
uv --version          # >= 0.7
node --version        # >= 18
```

**RHEL/CentOS：**

```bash
# 启用 EPEL 和 Python 3.12
sudo dnf install -y epel-release
sudo dnf install -y python3.12 python3.12-devel python3.12-pip \
    git curl gcc make libffi-devel openssl-devel

# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env
```

### 4.2 创建服务用户

```bash
# 创建专用用户
sudo useradd -r -m -s /bin/bash octop
sudo usermod -aG docker octop  # 如需 Docker 后端

# 创建数据目录
sudo mkdir -p /opt/octop
sudo mkdir -p /var/lib/octop
sudo chown octop:octop /opt/octop
sudo chown octop:octop /var/lib/octop
```

### 4.3 安装 Octop

```bash
# 切换到服务用户
sudo su - octop

# 克隆代码
cd /opt/octop
git clone https://github.com/TencentCloud/Octop.git .

# 创建虚拟环境
uv venv .venv
source .venv/bin/activate

# 安装 Octop
uv pip install -e .

# 或从 PyPI 安装 (稳定版)
uv pip install octop

# 构建前端 (可选，内置 dashboard 已包含)
# make build-frontend

# 验证安装
octop version
```

### 4.4 初始化配置

```bash
# 设置 OCTOP_HOME
export OCTOP_HOME=/var/lib/octop
echo 'export OCTOP_HOME=/var/lib/octop' >> ~/.bashrc

# 初始化数据库
octop init --yes

# 或直接创建配置文件
cat > /var/lib/octop/config.json << 'EOF'
{
  "bind_host": "127.0.0.1",
  "port": 8088,
  "log_level": "info",
  "default_timezone": "Asia/Shanghai",
  "enable_dashboard": true,
  "enable_api_docs": false,
  "database": {
    "driver": "sqlite",
    "sqlite_path": "octop.db"
  }
}
EOF

# 设置环境变量
cat > /var/lib/octop/env << 'EOF'
OCTOP_ADMIN_USERNAME=admin
OCTOP_ADMIN_PASSWORD=YourStrongPassword123
OPENAI_API_KEY=sk-your-key-here
EOF

chmod 600 /var/lib/octop/env
```

### 4.5 手动启动测试

```bash
# 前台启动 (测试用)
octop run --host 0.0.0.0 --port 8088

# 或指定配置
OCTOP_HOME=/var/lib/octop octop run
```

---

## 5. PostgreSQL 配置

### 5.1 安装 PostgreSQL

**Ubuntu/Debian：**

```bash
# 安装 PostgreSQL 16 + pgvector
sudo apt install -y postgresql-16 postgresql-16-pgvector

# 启动服务
sudo systemctl enable postgresql
sudo systemctl start postgresql
```

**RHEL/CentOS：**

```bash
# 添加 PostgreSQL 仓库
sudo dnf install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-9-x86_64/pgdg-redhat-repo-latest.noarch.rpm
sudo dnf install -y postgresql16-server postgresql16-contrib

# 初始化数据库
sudo /usr/pgsql-16/bin/postgresql-16-setup initdb

# 启动服务
sudo systemctl enable postgresql-16
sudo systemctl start postgresql-16
```

### 5.2 创建数据库和用户

```bash
# 切换到 postgres 用户
sudo -i -u postgres

# 创建用户和数据库
psql << 'EOF'
CREATE USER octop WITH PASSWORD 'your-secure-password';
CREATE DATABASE octop OWNER octop;

-- 启用 pgvector 扩展 (用于知识库向量搜索)
\c octop
CREATE EXTENSION IF NOT EXISTS vector;

-- 验证
\dx
\q
EOF

exit
```

### 5.3 配置 Octop 使用 PostgreSQL

**方式 1：环境变量**

```bash
# /var/lib/octop/env
OCTOP_DATABASE_DRIVER=postgresql
OCTOP_DATABASE_HOST=127.0.0.1
OCTOP_DATABASE_PORT=5432
OCTOP_DATABASE_NAME=octop
OCTOP_DATABASE_USER=octop
OCTOP_DATABASE_PASSWORD=your-secure-password

# 或使用完整 URL
OCTOP_DATABASE_URL=postgresql://octop:your-secure-password@127.0.0.1:5432/octop
```

**方式 2：config.json**

```json
{
  "database": {
    "driver": "postgresql",
    "host": "127.0.0.1",
    "port": 5432,
    "database": "octop",
    "user": "octop",
    "password": "your-secure-password"
  }
}
```

### 5.4 PostgreSQL 调优

```bash
# /etc/postgresql/16/main/postgresql.conf (Ubuntu)

# 连接
max_connections = 200
listen_addresses = 'localhost'  # 仅本地访问

# 内存 (根据服务器内存调整)
shared_buffers = 2GB            # 约 25% 总内存
effective_cache_size = 6GB      # 约 75% 总内存
work_mem = 32MB
maintenance_work_mem = 512MB

# WAL
wal_buffers = 64MB
min_wal_size = 1GB
max_wal_size = 4GB

# 日志
log_destination = 'csvlog'
logging_collector = on
log_directory = 'log'
log_filename = 'postgresql-%Y-%m-%d.log'
log_rotation_age = 1d
log_rotation_size = 100MB
log_min_duration_statement = 1000  # 记录慢查询 (>1s)
```

### 5.5 备份 PostgreSQL

```bash
# 手动备份
sudo -u postgres pg_dump -Fc octop > /backup/octop-db-$(date +%Y%m%d).dump

# 恢复
sudo -u postgres pg_restore -d octop -c /backup/octop-db-YYYYMMDD.dump

# 自动备份 (crontab)
# crontab -e
0 4 * * * /usr/bin/pg_dump -Fc octop | gzip > /backup/octop-db-$(date +\%Y\%m\%d).dump.gz
```

---

## 6. 配置详解

### 6.1 配置文件位置

| 文件 | 路径 | 说明 |
|------|------|------|
| 主配置 | `$OCTOP_HOME/config.json` | 核心配置 |
| 环境变量 | `$OCTOP_HOME/env` | 敏感信息 (API Key 等) |
| 数据库 | `$OCTOP_HOME/octop.db` | SQLite 数据库 |
| 日志 | `$OCTOP_HOME/logs/` | 日志文件 |

默认 `OCTOP_HOME=~/.octop`。

### 6.2 config.json 完整参考

```json
{
  // 网络
  "bind_host": "127.0.0.1",       // 监听地址 (生产用 127.0.0.1 + 反向代理)
  "port": 8088,                    // 监听端口

  // 日志
  "log_level": "info",             // debug | info | warning | error

  // 认证
  "access_token_ttl_seconds": 86400,    // JWT 令牌有效期 (秒)
  "login_max_attempts": 5,              // 登录失败锁定阈值
  "login_lockout_seconds": 900,         // 锁定时长 (秒)

  // 国际化
  "default_timezone": "Asia/Shanghai",  // 时区

  // CORS
  "cors_origins": [],                   // 允许的跨域来源

  // 功能开关
  "enable_dashboard": true,             // 启用 Dashboard UI
  "enable_api_docs": false,             // 启用 API 文档 (/api/docs)
  "require_setup_password": true,       // 首次设置需要密码

  // 上传
  "max_upload_mb": 100,                 // 最大上传大小 (1-1024 MB)

  // 浏览器
  "browser_idle_timeout_minutes": 30,   // 浏览器空闲超时

  // 数据库
  "database": {
    "driver": "sqlite",                 // sqlite | postgresql
    "sqlite_path": "octop.db",          // SQLite 文件路径
    "host": "127.0.0.1",                // PostgreSQL 主机
    "port": 5432,                       // PostgreSQL 端口
    "database": "octop",                // PostgreSQL 数据库名
    "user": "octop",                    // PostgreSQL 用户
    "password": ""                      // PostgreSQL 密码
  },

  // TLS
  "tls": {
    "enabled": false,
    "mode": "acme",                     // acme | manual
    "domains": [],
    "cert_file": "",
    "key_file": "",
    "acme_staging": false,
    "http_port": 80
  },

  // 自动备份
  "backup": {
    "auto_enabled": false,
    "schedule": "cron:0 4 * * *",       // 每天凌晨 4 点
    "retention_count": 7,               // 保留 7 份
    "include_config": true,
    "include_workspaces": true,
    "include_skill_packages": true,
    "include_plugins": true,
    "include_knowledge": true,
    "include_chats": true
  }
}
```

### 6.3 环境变量完整列表

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OCTOP_HOME` | `~/.octop` | 数据根目录 |
| `OCTOP_BIND_HOST` | `127.0.0.1` | 监听地址 |
| `OCTOP_PORT` | `8088` | 监听端口 |
| `OCTOP_LOG_LEVEL` | `info` | 日志级别 |
| `OCTOP_LOG_RETENTION_DAYS` | `14` | 日志保留天数 |
| `OCTOP_LOG_MAX_BYTES` | `104857600` | 日志文件大小上限 (100MB) |
| `OCTOP_LOG_COMPRESS` | `true` | 压缩旧日志 |
| `OCTOP_ACCESS_TOKEN_TTL` | `86400` | JWT 有效期 (秒) |
| `OCTOP_LOGIN_MAX_ATTEMPTS` | `5` | 登录失败锁定阈值 |
| `OCTOP_LOGIN_LOCKOUT_SECONDS` | `900` | 锁定时长 (秒) |
| `OCTOP_DEFAULT_TIMEZONE` | `Asia/Shanghai` | 默认时区 |
| `OCTOP_CORS_ORIGINS` | (空) | CORS 允许来源 (逗号分隔) |
| `OCTOP_ENABLE_DASHBOARD` | `true` | 启用 Dashboard |
| `OCTOP_ENABLE_API_DOCS` | `false` | 启用 API 文档 |
| `OCTOP_REQUIRE_SETUP_PASSWORD` | `true` | 设置向导需要密码 |
| `OCTOP_MAX_UPLOAD_MB` | `100` | 上传大小限制 |
| `OCTOP_BROWSER_IDLE_TIMEOUT_MINUTES` | `30` | 浏览器空闲超时 |
| `OCTOP_DATABASE_URL` | - | 数据库完整 URL |
| `OCTOP_DATABASE_DRIVER` | `sqlite` | 数据库驱动 |
| `OCTOP_DATABASE_SQLITE_PATH` | `octop.db` | SQLite 路径 |
| `OCTOP_DATABASE_HOST` | `127.0.0.1` | PostgreSQL 主机 |
| `OCTOP_DATABASE_PORT` | `5432` | PostgreSQL 端口 |
| `OCTOP_DATABASE_NAME` | `octop` | PostgreSQL 数据库名 |
| `OCTOP_DATABASE_USER` | `octop` | PostgreSQL 用户 |
| `OCTOP_DATABASE_PASSWORD` | - | PostgreSQL 密码 |
| `OCTOP_BACKUP_AUTO_ENABLED` | `false` | 启用自动备份 |
| `OCTOP_BACKUP_SCHEDULE` | `cron:0 4 * * *` | 备份计划 |
| `OCTOP_BACKUP_RETENTION_COUNT` | `7` | 备份保留数 |
| `OCTOP_ADMIN_USERNAME` | - | 管理员用户名 |
| `OCTOP_ADMIN_PASSWORD` | - | 管理员密码 |
| `OCTOP_CAPTCHA_PROVIDER` | `slider` | 验证码类型 |
| `OCTOP_CAPTCHA_SITE_KEY` | - | 验证码公钥 |
| `OCTOP_CAPTCHA_SECRET` | - | 验证码密钥 |
| `OPENAI_API_KEY` | - | OpenAI API Key |
| `DASHSCOPE_API_KEY` | - | 阿里云 DashScope Key |
| `LANGFUSE_PUBLIC_KEY` | - | Langfuse 公钥 |
| `LANGFUSE_SECRET_KEY` | - | Langfuse 私钥 |
| `LANGFUSE_HOST` | - | Langfuse 主机 |

---

## 7. TLS/SSL 证书

### 7.1 方式一：Octop 内置 ACME (Let's Encrypt)

**前提条件：**

- 域名已解析到服务器公网 IP
- 80 端口可从外网访问 (用于 ACME 验证)
- 防火墙允许 80 和 443 端口

**配置：**

```json
// config.json
{
  "tls": {
    "enabled": true,
    "mode": "acme",
    "domains": ["octop.example.com"],
    "acme_staging": false,
    "http_port": 80
  }
}
```

```bash
# 通过 API 签发证书
curl -X POST http://localhost:8088/api/admin/tls/issue \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"domains": ["octop.example.com"]}'
```

**自动续期：** Octop 内置续期任务，证书到期前自动续签。

### 7.2 方式二：手动证书

```json
// config.json
{
  "tls": {
    "enabled": true,
    "mode": "manual",
    "cert_file": "/etc/ssl/certs/octop.crt",
    "key_file": "/etc/ssl/private/octop.key"
  }
}
```

```bash
# 确保证书文件权限正确
sudo chown octop:octop /etc/ssl/private/octop.key
chmod 600 /etc/ssl/private/octop.key
```

### 7.3 方式三：Nginx 反向代理处理 TLS

推荐在生产环境中使用 Nginx 处理 TLS，Octop 仅监听本地 HTTP。详见 [§9 反向代理](#9-反向代理-nginx)。

---

## 8. 系统服务 (systemd)

### 8.1 创建 systemd 服务文件

```bash
sudo tee /etc/systemd/system/octop.service > /dev/null << 'EOF'
[Unit]
Description=Octop AI Assistant Platform
Documentation=https://github.com/TencentCloud/Octop
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=octop
Group=octop

# 环境变量
Environment=OCTOP_HOME=/var/lib/octop
EnvironmentFile=/var/lib/octop/env

# 工作目录
WorkingDirectory=/opt/octop

# 启动命令
ExecStart=/opt/octop/.venv/bin/octop run --host 127.0.0.1 --port 8088

# 重启策略
Restart=on-failure
RestartSec=10
StartLimitIntervalSec=60
StartLimitBurst=3

# 资源限制
LimitNOFILE=65535
LimitNPROC=4096

# 安全加固
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/octop
PrivateTmp=true

# 日志
StandardOutput=journal
StandardError=journal
SyslogIdentifier=octop

[Install]
WantedBy=multi-user.target
EOF
```

### 8.2 管理服务

```bash
# 重载 systemd
sudo systemctl daemon-reload

# 启用开机自启
sudo systemctl enable octop

# 启动/停止/重启
sudo systemctl start octop
sudo systemctl stop octop
sudo systemctl restart octop

# 查看状态
sudo systemctl status octop

# 查看日志
sudo journalctl -u octop -f
sudo journalctl -u octop --since "1 hour ago"
sudo journalctl -u octop -n 100
```

### 8.3 使用 Octop 内置服务管理

Octop 也提供内置的 systemd 服务管理：

```bash
# 安装系统服务
octop service install

# 启动/停止
octop service start
octop service stop

# 查看状态
octop service status

# 重启
octop service restart
```

### 8.4 服务文件说明

| 配置项 | 说明 |
|--------|------|
| `LimitNOFILE=65535` | 文件描述符限制 (Agent 并发需要) |
| `Restart=on-failure` | 崩溃后自动重启 |
| `ProtectSystem=strict` | 系统目录只读保护 |
| `ReadWritePaths=/var/lib/octop` | 仅允许写入数据目录 |
| `PrivateTmp=true` | 独立 /tmp 目录 |
| `NoNewPrivileges=true` | 禁止提权 |

---

## 9. 反向代理 (Nginx)

### 9.1 安装 Nginx

```bash
sudo apt install -y nginx
sudo systemctl enable nginx
```

### 9.2 Nginx 配置

**HTTP (重定向到 HTTPS)：**

```nginx
# /etc/nginx/sites-available/octop

server {
    listen 80;
    listen [::]:80;
    server_name octop.example.com;

    # ACME 证书验证 (如使用 Octop 内置 ACME)
    location /.well-known/acme-challenge/ {
        proxy_pass http://127.0.0.1:8088;
    }

    # 其他请求重定向到 HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}
```

**HTTPS：**

```nginx
# /etc/nginx/sites-available/octop

# HTTP/2 + HTTPS
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name octop.example.com;

    # TLS 证书
    ssl_certificate /etc/letsencrypt/live/octop.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/octop.example.com/privkey.pem;

    # TLS 配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:10m;
    ssl_session_tickets off;

    # HSTS
    add_header Strict-Transport-Security "max-age=63072000" always;

    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # 上传大小
    client_max_body_size 100M;

    # API 和 WebSocket
    location /api/ {
        proxy_pass http://127.0.0.1:8088;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE 支持
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }

    # WebSocket
    location /ws/ {
        proxy_pass http://127.0.0.1:8088;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400s;
    }

    # Dashboard (静态文件缓存)
    location /assets/ {
        proxy_pass http://127.0.0.1:8088;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_cache_valid 200 1y;
        add_header Cache-Control "public, immutable";
    }

    # 其他请求
    location / {
        proxy_pass http://127.0.0.1:8088;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 9.3 启用配置

```bash
# 创建软链接
sudo ln -s /etc/nginx/sites-available/octop /etc/nginx/sites-enabled/

# 删除默认配置
sudo rm /etc/nginx/sites-enabled/default

# 测试配置
sudo nginx -t

# 重载 Nginx
sudo systemctl reload nginx
```

### 9.4 Let's Encrypt 证书 (Certbot)

```bash
# 安装 Certbot
sudo apt install -y certbot python3-certbot-nginx

# 签发证书
sudo certbot --nginx -d octop.example.com

# 自动续期 (已自动配置 cron)
sudo certbot renew --dry-run
```

---

## 10. 备份与恢复

### 10.1 备份策略

| 数据类型 | 备份方式 | 频率 | 保留 |
|---------|---------|------|------|
| 数据库 | pg_dump / SQLite 复制 | 每日 | 7-30 天 |
| 配置文件 | 文件复制 | 每日 | 7 天 |
| Agent 工作空间 | tar 归档 | 每周 | 4 周 |
| 技能包/插件 | tar 归档 | 每周 | 4 周 |
| 知识库 | tar 归档 | 每周 | 4 周 |

### 10.2 使用 Octop 内置备份

```bash
# 手动创建备份
octop backup create

# 列出备份
octop backup list

# 恢复备份
octop backup restore <backup_file>

# 配置自动备份
# config.json
{
  "backup": {
    "auto_enabled": true,
    "schedule": "cron:0 4 * * *",
    "retention_count": 7,
    "include_config": true,
    "include_workspaces": true,
    "include_skill_packages": true,
    "include_plugins": true,
    "include_knowledge": true,
    "include_chats": true
  }
}
```

### 10.3 手动备份脚本

```bash
#!/bin/bash
# /usr/local/bin/octop-backup.sh

set -euo pipefail

BACKUP_DIR="/backup/octop"
DATA_DIR="/var/lib/octop"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting backup..."

# 备份数据库
if [ -f "$DATA_DIR/octop.db" ]; then
    # SQLite: 直接复制 (WAL 模式下安全)
    sqlite3 "$DATA_DIR/octop.db" "VACUUM INTO '$BACKUP_DIR/octop-db-$DATE.db'"
    gzip "$BACKUP_DIR/octop-db-$DATE.db"
    echo "  Database backed up"
else
    # PostgreSQL: pg_dump
    sudo -u postgres pg_dump -Fc octop | gzip > "$BACKUP_DIR/octop-db-$DATE.dump.gz"
    echo "  PostgreSQL dumped"
fi

# 备份配置
tar czf "$BACKUP_DIR/octop-config-$DATE.tar.gz" \
    -C "$DATA_DIR" \
    config.json env secrets/ 2>/dev/null || true
echo "  Config backed up"

# 备份 Agent 工作空间
tar czf "$BACKUP_DIR/octop-agents-$DATE.tar.gz" \
    -C "$DATA_DIR" \
    agents/ 2>/dev/null || true
echo "  Agents backed up"

# 备份技能包和插件
tar czf "$BACKUP_DIR/octop-skills-$DATE.tar.gz" \
    -C "$DATA_DIR" \
    skill_packages/ plugins/ 2>/dev/null || true
echo "  Skills/Plugins backed up"

# 清理旧备份
find "$BACKUP_DIR" -name "*.gz" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete
echo "  Old backups cleaned"

echo "[$(date)] Backup completed: $BACKUP_DIR"
ls -lh "$BACKUP_DIR"/*$DATE*
```

```bash
# 添加执行权限
sudo chmod +x /usr/local/bin/octop-backup.sh

# 添加 crontab
# crontab -e
0 4 * * * /usr/local/bin/octop-backup.sh >> /var/log/octop-backup.log 2>&1
```

### 10.4 恢复流程

```bash
# 1. 停止服务
sudo systemctl stop octop

# 2. 恢复数据库 (SQLite)
cp /backup/octop-db-20260928.db /var/lib/octop/octop.db

# 或恢复 PostgreSQL
sudo -u postgres pg_restore -d octop -c /backup/octop-db-20260928.dump

# 3. 恢复配置和工作空间
cd /var/lib/octop
tar xzf /backup/octop-config-20260928.tar.gz
tar xzf /backup/octop-agents-20260928.tar.gz

# 4. 修复权限
chown -R octop:octop /var/lib/octop

# 5. 启动服务
sudo systemctl start octop

# 6. 验证
curl http://localhost:8088/api/health
```

---

## 11. 监控与日志

### 11.1 健康检查

```bash
# HTTP 健康检查
curl -f http://localhost:8088/api/health

# 详细状态
curl http://localhost:8088/api/health | jq .

# Docker 环境
docker compose exec octop curl -f http://localhost:8088/api/health
```

### 11.2 日志管理

**日志位置：**

| 环境 | 日志路径 |
|------|---------|
| 裸机 | `$OCTOP_HOME/logs/octop.log` |
| Docker | `docker compose logs` 或 `/var/lib/docker/containers/...` |
| systemd | `journalctl -u octop` |

**日志轮转配置：**

Octop 内置日志轮转：

- 按天轮转 (午夜)
- 按大小轮转 (默认 100MB)
- 自动压缩 (gzip)
- 保留天数 (默认 14 天)

```bash
# 调整日志配置
# config.json 或环境变量
{
  "log_level": "info",
}

# 环境变量
OCTOP_LOG_RETENTION_DAYS=30
OCTOP_LOG_MAX_BYTES=209715200  # 200MB
OCTOP_LOG_COMPRESS=true
```

**查看日志：**

```bash
# 实时跟踪
tail -f /var/lib/octop/logs/octop.log

# 查看错误
grep -i error /var/lib/octop/logs/octop.log | tail -50

# 查看特定 Agent 日志
grep "agent_id=xxx" /var/lib/octop/logs/octop.log

# 查看今天的日志
grep "$(date +%Y-%m-%d)" /var/lib/octop/logs/octop.log
```

### 11.3 Prometheus 监控 (可选)

Octop 内置基础指标，可通过 `/api/metrics` 暴露 (如已实现)：

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'octop'
    scrape_interval: 15s
    metrics_path: '/api/metrics'
    static_configs:
      - targets: ['localhost:8088']
```

### 11.4 Uptime 监控

```bash
# 简单监控脚本
#!/bin/bash
# /usr/local/bin/octop-monitor.sh

HEALTH_URL="http://localhost:8088/api/health"
ALERT_EMAIL="admin@example.com"

if ! curl -sf "$HEALTH_URL" > /dev/null; then
    echo "Octop is down at $(date)" | mail -s "Octop Alert" "$ALERT_EMAIL"
    sudo systemctl restart octop
fi
```

```bash
# crontab
*/5 * * * * /usr/local/bin/octop-monitor.sh
```

---

## 12. 安全加固

### 12.1 网络安全

**防火墙配置 (UFW)：**

```bash
# 启用防火墙
sudo ufw enable

# 允许 SSH
sudo ufw allow 22/tcp

# 允许 HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 不直接暴露 Octop (通过 Nginx 反向代理)
# sudo ufw allow 8088/tcp  # 不需要

# 查看状态
sudo ufw status
```

**防火墙配置 (firewalld)：**

```bash
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### 12.2 应用安全

**强密码策略：**

Octop 内置密码策略：

- 最少 8 个字符
- 必须包含字母和数字
- 常见弱密码黑名单
- 不能与旧密码相同

**启用验证码：**

```bash
# config.json 或环境变量
OCTOP_CAPTCHA_PROVIDER=slider
OCTOP_CAPTCHA_SITE_KEY=your-site-key
OCTOP_CAPTCHA_SECRET=your-secret-key
```

**限制登录尝试：**

```json
{
  "login_max_attempts": 5,
  "login_lockout_seconds": 900
}
```

**JWT 令牌有效期：**

```json
{
  "access_token_ttl_seconds": 86400  // 24 小时
}
```

### 12.3 文件权限

```bash
# 数据目录
sudo chown -R octop:octop /var/lib/octop
chmod 700 /var/lib/octop
chmod 600 /var/lib/octop/config.json
chmod 600 /var/lib/octop/env
chmod 600 /var/lib/octop/secrets/*

# 日志目录
chmod 750 /var/lib/octop/logs

# 证书文件
sudo chown octop:octop /etc/ssl/private/octop.key
chmod 600 /etc/ssl/private/octop.key
```

### 12.4 数据库安全

**PostgreSQL：**

```bash
# 仅允许本地连接
# /etc/postgresql/16/main/pg_hba.conf
local   all             all                                     peer
host    all             all             127.0.0.1/32            scram-sha-256
host    all             all             ::1/128                 scram-sha-256

# 不使用 md5，使用 scram-sha-256
# postgresql.conf
password_encryption = scram-sha-256
```

**SQLite：**

```bash
# 确保数据库文件权限
chmod 600 /var/lib/octop/octop.db
```

### 12.5 API 安全

**禁用 API 文档 (生产环境)：**

```json
{
  "enable_api_docs": false
}
```

**配置 CORS：**

```json
{
  "cors_origins": ["https://octop.example.com"]
}
```

**禁用 Dashboard (仅 API)：**

```json
{
  "enable_dashboard": false
}
```

### 12.6 安全审计

```bash
# 查看审计日志
octop admin audit-log

# 查看活跃用户
octop user list --active

# 查看 Agent 使用情况
octop agent list --json
```

---

## 13. 性能调优

### 13.1 系统级调优

**文件描述符：**

```bash
# /etc/security/limits.conf
octop soft nofile 65535
octop hard nofile 65535

# 或在 systemd 服务文件中
LimitNOFILE=65535
```

**内核参数：**

```bash
# /etc/sysctl.conf
# 增加 TCP 连接队列
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535

# 增加本地端口范围
net.ipv4.ip_local_port_range = 1024 65535

# 启用 TCP Fast Open
net.ipv4.tcp_fastopen = 3

# 应用
sudo sysctl -p
```

### 13.2 Python/uvicorn 调优

**Worker 进程 (多核)：**

```bash
# 注意：Octop 单进程模型，多 worker 可能导致状态不一致
# 仅在只读场景下使用多 worker
octop run --workers 4
```

**推荐：使用单 worker + 反向代理负载均衡**

### 13.3 数据库调优

**SQLite：**

```python
# SQLite WAL 模式已默认启用
# 调整缓存大小 (在 config.py 中)
PRAGMA cache_size = -64000  # 64MB
PRAGMA synchronous = NORMAL  # 平衡性能和安全
```

**PostgreSQL：**

参见 [§5.4 PostgreSQL 调优](#54-postgresql-调优)。

### 13.4 Agent 并发

```bash
# 限制同时运行的 Agent 数量
# 在用户策略中设置
{
  "max_agents": 10
}
```

### 13.5 内存管理

```bash
# 限制 Agent 内存使用 (Docker 后端)
# config.json 中 Agent 配置
{
  "backend": {
    "kind": "docker",
    "memory": "2g",
    "cpus": "2"
  }
}
```

### 13.6 缓存策略

**前端静态资源：**

Nginx 配置中已包含缓存头：

```nginx
location /assets/ {
    proxy_cache_valid 200 1y;
    add_header Cache-Control "public, immutable";
}
```

**API 响应缓存：**

Octop 当前不内置 API 缓存，可通过 Nginx 或 CDN 缓存静态 API 响应。

---

## 14. 升级指南

### 14.1 升级前检查

```bash
# 1. 查看当前版本
octop version

# 2. 查看最新版本
# 访问 https://github.com/TencentCloud/Octop/releases

# 3. 阅读 CHANGELOG
# https://github.com/TencentCloud/Octop/blob/main/CHANGELOG.md

# 4. 备份数据
octop backup create
```

### 14.2 Docker 升级

```bash
# 1. 拉取最新镜像
cd docker
docker compose pull

# 或重新构建
docker compose build --no-cache

# 2. 停止旧容器
docker compose down

# 3. 启动新容器
docker compose up -d

# 4. 检查日志
docker compose logs -f

# 5. 验证健康
docker compose exec octop octop version
curl http://localhost:8088/api/health
```

### 14.3 裸机升级

```bash
# 1. 停止服务
sudo systemctl stop octop

# 2. 备份
octop backup create

# 3. 更新代码
cd /opt/octop
git fetch origin
git checkout v1.0.3  # 替换为目标版本

# 4. 更新依赖
source .venv/bin/activate
uv pip install -e .

# 5. 运行迁移 (自动)
# 数据库迁移在服务启动时自动执行

# 6. 启动服务
sudo systemctl start octop

# 7. 验证
octop version
curl http://localhost:8088/api/health
```

### 14.4 从 PyPI 升级

```bash
# 停止服务
sudo systemctl stop octop

# 升级
source /opt/octop/.venv/bin/activate
uv pip install --upgrade octop

# 启动
sudo systemctl start octop
```

### 14.5 数据库迁移

数据库迁移在服务启动时自动执行。如需手动检查：

```bash
# 查看当前 schema 版本
octop admin db-version

# 手动运行迁移 (通常不需要)
octop admin migrate
```

---

## 15. 故障排查

### 15.1 服务无法启动

**症状：** `systemctl start octop` 失败

```bash
# 查看详细错误
sudo journalctl -u octop -n 50

# 常见原因：
# 1. 端口被占用
sudo ss -tlnp | grep 8088

# 2. 权限问题
ls -la /var/lib/octop/

# 3. 配置错误
cat /var/lib/octop/config.json | python3 -m json.tool

# 4. 数据库锁定
lsof /var/lib/octop/octop.db
```

### 15.2 Agent 无法启动

```bash
# 查看 Agent 状态
octop agent list --json

# 查看 Agent 错误
octop agent get <agent_id> --json

# 重启 Agent
octop agent restart <agent_id>

# 查看日志
grep "agent_id=<agent_id>" /var/lib/octop/logs/octop.log
```

### 15.3 LLM 调用失败

```bash
# 检查 API Key
octop provider list

# 测试提供商
octop provider test <provider_name>

# 查看错误日志
grep -i "openai\|llm\|provider" /var/lib/octop/logs/octop.log | tail -20
```

### 15.4 WebSocket 连接断开

```bash
# 检查 Nginx 配置
# 确保 WebSocket 代理正确
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
proxy_read_timeout 86400s;

# 检查防火墙
# 确保 443 端口允许长连接
```

### 15.5 数据库连接失败

```bash
# SQLite
ls -la /var/lib/octop/octop.db
sqlite3 /var/lib/octop/octop.db "PRAGMA integrity_check;"

# PostgreSQL
psql -h 127.0.0.1 -U octop -d octop -c "SELECT 1;"

# 检查连接配置
cat /var/lib/octop/config.json | jq .database
```

### 15.6 内存不足

```bash
# 查看内存使用
free -h
docker stats octop

# 限制 Agent 内存
# config.json
{
  "backend": {
    "kind": "docker",
    "memory": "1g"
  }
}

# 重启服务释放内存
sudo systemctl restart octop
```

### 15.7 磁盘空间不足

```bash
# 查看磁盘使用
df -h
du -sh /var/lib/octop/*

# 清理旧日志
find /var/lib/octop/logs -name "*.gz" -mtime +30 -delete

# 清理旧备份
find /backup/octop -mtime +30 -delete

# 清理 Docker (如使用)
docker system prune -af
docker volume prune -f
```

---

## 16. 运维命令速查

### 16.1 服务管理

| 操作 | 命令 |
|------|------|
| 启动服务 | `sudo systemctl start octop` |
| 停止服务 | `sudo systemctl stop octop` |
| 重启服务 | `sudo systemctl restart octop` |
| 查看状态 | `sudo systemctl status octop` |
| 开机自启 | `sudo systemctl enable octop` |
| 禁用自启 | `sudo systemctl disable octop` |
| 查看日志 | `sudo journalctl -u octop -f` |

### 16.2 CLI 命令

| 操作 | 命令 |
|------|------|
| 查看版本 | `octop version` |
| 列出用户 | `octop user list` |
| 列出 Agent | `octop agent list` |
| 启动 Agent | `octop agent start <id>` |
| 停止 Agent | `octop agent stop <id>` |
| 重启 Agent | `octop agent restart <id>` |
| 创建备份 | `octop backup create` |
| 列出备份 | `octop backup list` |
| 恢复备份 | `octop backup restore <file>` |
| 查看配置 | `octop config show` |
| 设置配置 | `octop config set <key> <value>` |

### 16.3 Docker 命令

| 操作 | 命令 |
|------|------|
| 启动 | `docker compose up -d` |
| 停止 | `docker compose down` |
| 重启 | `docker compose restart` |
| 查看日志 | `docker compose logs -f` |
| 进入容器 | `docker compose exec octop bash` |
| 执行 CLI | `docker compose exec octop octop <cmd>` |
| 更新镜像 | `docker compose pull && docker compose up -d` |
| 查看资源 | `docker stats octop` |

### 16.4 健康检查

| 操作 | 命令 |
|------|------|
| HTTP 健康 | `curl http://localhost:8088/api/health` |
| 数据库检查 | `octop admin db-status` |
| Agent 状态 | `octop agent list --json` |
| 磁盘空间 | `df -h /var/lib/octop` |
| 内存使用 | `free -h` |
| 日志错误 | `grep -i error /var/lib/octop/logs/octop.log \| tail` |

### 16.5 常用文件路径

| 文件 | 路径 |
|------|------|
| 配置 | `/var/lib/octop/config.json` |
| 环境变量 | `/var/lib/octop/env` |
| 数据库 | `/var/lib/octop/octop.db` |
| 日志 | `/var/lib/octop/logs/octop.log` |
| Agent 数据 | `/var/lib/octop/agents/` |
| 插件 | `/var/lib/octop/plugins/` |
| 技能包 | `/var/lib/octop/skill_packages/` |
| TLS 证书 | `/var/lib/octop/ssl/` |
| systemd 服务 | `/etc/systemd/system/octop.service` |
| Nginx 配置 | `/etc/nginx/sites-available/octop` |

---

## 附录 A：完整部署检查清单

### 首次部署

- [ ] 系统要求满足 (CPU/内存/磁盘)
- [ ] 防火墙配置完成 (80/443 开放)
- [ ] DNS 解析配置 (如使用域名)
- [ ] 安装 Docker 或系统依赖
- [ ] 创建服务用户 (裸机部署)
- [ ] 配置环境变量 (API Key、密码等)
- [ ] 初始化数据库
- [ ] 启动服务
- [ ] 验证健康检查 (`/api/health`)
- [ ] 配置 TLS 证书
- [ ] 配置反向代理 (Nginx)
- [ ] 配置 systemd 服务 (裸机部署)
- [ ] 配置自动备份
- [ ] 配置日志轮转
- [ ] 安全加固 (密码策略、验证码等)

### 日常运维

- [ ] 每日检查服务状态
- [ ] 每日检查磁盘空间
- [ ] 每周检查备份完整性
- [ ] 每月审查安全日志
- [ ] 定期更新系统包
- [ ] 定期更新 Octop 版本

---

## 附录 B：环境变量快速参考

```bash
# === 基础配置 ===
OCTOP_HOME=/var/lib/octop
OCTOP_BIND_HOST=0.0.0.0
OCTOP_PORT=8088
OCTOP_LOG_LEVEL=info

# === 管理员 ===
OCTOP_ADMIN_USERNAME=admin
OCTOP_ADMIN_PASSWORD=YourStrongPassword123

# === 数据库 ===
OCTOP_DATABASE_DRIVER=postgresql
OCTOP_DATABASE_HOST=127.0.0.1
OCTOP_DATABASE_PORT=5432
OCTOP_DATABASE_NAME=octop
OCTOP_DATABASE_USER=octop
OCTOP_DATABASE_PASSWORD=your-secure-password

# === LLM 提供商 ===
OPENAI_API_KEY=sk-...
DASHSCOPE_API_KEY=sk-...

# === 可观测性 ===
LANGFUSE_PUBLIC_KEY=pk-...
LANGFUSE_SECRET_KEY=sk-...
LANGFUSE_HOST=https://langfuse.example.com

# === 验证码 ===
OCTOP_CAPTCHA_PROVIDER=slider
OCTOP_CAPTCHA_SITE_KEY=your-site-key
OCTOP_CAPTCHA_SECRET=your-secret-key
```

---

> **更多信息：**
>
> - 官方文档：https://github.com/TencentCloud/Octop
> - API 文档：启动后访问 `/api/docs`
> - 问题反馈：https://github.com/TencentCloud/Octop/issues
