# dbtune

`dbtune` 是一个面向 PostgreSQL 的自动索引调优原型项目，目标是把“工作负载观察 + 索引建议 + 数据库扩展能力”串成可迭代的调优闭环。

## 项目意义

- 降低手工调优门槛：把经验型索引调优流程工具化。
- 支持在线演进：通过服务化接口持续接收查询并触发调优逻辑。
- 连接研究与工程：将 MAB（多臂老虎机）策略与 PG 扩展联动验证。

## 当前组成

- `dbtune_mab_service/`：FastAPI + Celery + Redis 的调优服务层。
- `dbtune_pg_mab_extension/`：PostgreSQL C 扩展（实验能力）。
- `docker-compose.yml`：本地一键拉起 PostgreSQL、Redis、API、Worker。

## 快速开始（Docker）

### 1) 启动

```bash
docker compose down --volumes --remove-orphans
docker compose up --build
```

### 2) 健康检查

```bash
curl -s http://127.0.0.1:5050/health
```

预期返回：

```json
{"status":"ok"}
```

### 3) 触发一次调优请求（示例）

```bash
curl -s -X POST http://127.0.0.1:5050/mab/tune_async \
  -H 'Content-Type: application/json' \
  -d '{
    "table": "users",
    "columns": ["age", "income"],
    "options": {
      "query_file": "/app/test_inputs/test.sql",
      "config_file": "/app/test_inputs/config.yaml"
    }
  }'
```

## 本地开发

### 运行测试

```bash
pytest -q
```

说明：

- 集成测试在外部依赖（PostgreSQL/Redis/服务）不可用时会自动 `skip`。
- 单元和配置测试默认可执行。

## 版本与发布策略

- 当前版本记录在根目录 `VERSION`，从 `0.1.0` 开始。
- 采用语义化版本（SemVer）：
  - `MAJOR`：不兼容变更
  - `MINOR`：向后兼容的新功能
  - `PATCH`：向后兼容的问题修复
- 每次版本变更必须同步更新：
  - `VERSION`
  - `CHANGELOG.md`
  - 如有用户可见行为变化，同步更新本 README。

## Changelog

- 变更记录见 [CHANGELOG.md](CHANGELOG.md)。
- 推荐每个小版本只做“少量可验证功能”，保持可回滚、可复现。

## 项目状态（v0.1.0 基线）

- 已具备：基础服务编排、健康检查接口、测试基线与版本化流程。
- 进行中：调优算法与真实工作负载联调、扩展能力增强、更多端到端验证。

