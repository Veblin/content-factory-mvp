# 内容工厂 MVP

一个面向个人创作者的小红书内容生产最小闭环：
输入选题关键词，自动完成热点筛选、选题推荐、图文草稿生成和配图 Prompt 扩写。

- 架构：6 Agent + 2 数据源 + 1 CLI 入口
- 依赖：3 个 Python 包
- 成本：单一 DeepSeek API Key

---

## 1. 项目功能

### 1.1 一键流水线（CLI）
运行一次命令后，系统会自动执行：

1. Scout：采集 B站 + 微博热点，并过滤 AI/AIGC/二次元/技术相关话题
2. Strategist：结合你的关键词与热点，生成 8-10 个候选选题池
3. ResonanceAnalyst：分析用户为什么会点进来，给出情绪入口与观看场景
4. EvidenceBuilder：生成内容 brief，补齐真实细节、结构和互动问题
5. Writer：基于 topic + resonance + brief 生成小红书草稿
6. ArtDirector：将 5 条基础描述扩写成 20 条候选配图 Prompt
7. 输出：自动写入 output 目录，便于你人工审核和发布

### 1.2 统一 LLM 调用
- Scout / ArtDirector：deepseek-chat
- Strategist / Writer：deepseek-reasoner
- 统一通过 llm_client.py 调用 DeepSeek API

### 1.3 最小但可用的内容交付
- 自动生成 Markdown 草稿
- 自动追加配图 Prompt 包
- 在成稿前先生成情绪洞察与内容 brief，减少模板腔
- 人工完成最后审核与发布（符合 MVP 定位）

---

## 2. 项目结构

```text
content-factory-mvp/
├── main.py
├── config.py
├── llm_client.py
├── agents/
│   ├── scout.py
│   ├── strategist.py
│   ├── resonance_analyst.py
│   ├── evidence_builder.py
│   ├── writer.py
│   └── art_director.py
├── crawlers/
│   ├── bilibili.py
│   └── weibo.py
├── data/
│   └── manual_topics.json
├── output/
├── .env.example
└── requirements.txt
```

---

## 3. 如何使用

### 3.1 环境要求
- Python 3.10+
- macOS / Linux / Windows（已在 macOS 验证）

### 3.2 安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3.3 配置 API Key

```bash
cp .env.example .env
```

编辑 .env，填入你的真实 Key：

```env
DEEPSEEK_API_KEY=sk-xxxx
```

### 3.4 运行项目

```bash
python main.py "AI绘画, ComfyUI教程, 二次元"
```

默认配图后端是 Nano Banana Pro（无需额外参数）：

```bash
python main.py "AI绘画, 二次元"
```

默认会给出 10 个候选选题，你可以一次选择 1 到 3 个：

```bash
python main.py "AI绘画, 二次元" --topic-count 10
```

如果要切换到 SDXL 系列模型：

```bash
python main.py "AI绘画, 二次元" --image-backend sdxl
```

不传参数时会使用默认关键词：

```bash
python main.py
```

### 3.5 运行结果
执行完成后会得到：

1. 终端中展示热点与选题推荐
2. 你可以在候选池中一次选择 1 到 3 个选题
3. output 目录下新增一个或多个 Markdown 草稿，文件名示例：
   - 2026-03-28-xxx.md
4. 每个草稿内包含：
   - 标题 + 正文 + 标签
   - 5 条基础配图描述
   - 20 条候选配图 Prompt

终端还会额外展示：
- 这条内容的情绪入口
- 更适合的内容结构类型
- 更具体的评论区引导问题

---

## 4. 日常工作流建议

单次约 20-30 分钟：

1. 运行命令生成草稿
2. 选择一个推荐选题
3. 人工微调文案（3-5 分钟）
4. 用配图 Prompt 在图像平台出图并筛选
5. 发布到小红书

---

## 5. Roadmap

### Phase 1（当前 MVP）
- 4 Agent（Scout / Strategist / Writer / ArtDirector）
- 2 数据源（B站 + 微博）
- CLI 单机运行
- 人工审核 + 手动出图

### Phase 2（提效）
- 接入更多数据源（知乎、GitHub Trending）
- 支持图片生成 API（自动生成与回传）
- 增加内容模板库（教程/清单/观点/复盘）
- 增加失败重试与日志追踪

### Phase 3（稳定化）
- 增加合规层（违禁词 + 语义风险检查）
- 增加版权/相似度检测（基础去重）
- 增加多平台改写（公众号、视频号）
- 增加质量评分与发布前 checklist

### Phase 4（自动化）
- Dispatcher 任务编排
- 定时任务与批量生产
- 运营看板（选题命中率、互动率、转化）
- 半自动/全自动发布链路

---

## 6. 常见问题

### Q1: 运行时报 401 / 403
- 检查 .env 是否存在
- 检查 DEEPSEEK_API_KEY 是否正确
- 检查 Key 是否可用、余额是否充足

### Q2: 微博数据抓取失败
- 程序会自动降级到 HTML 抓取
- 如仍失败，可稍后重试（可能是网络或目标站限流）

### Q3: LLM 返回 JSON 解析失败
- 系统已做代码块包裹兼容处理
- 若仍失败，建议在对应 Agent prompt 中继续收紧输出约束

---

## 7. 开发说明

### 7.1 代码检查

```bash
python -m py_compile main.py config.py llm_client.py agents/*.py crawlers/*.py
```

### 7.2 依赖列表
- httpx
- beautifulsoup4
- python-dotenv

---

## 8. License

当前仓库未声明开源协议。
如需对外发布，建议补充 MIT 或 Apache-2.0 License。
