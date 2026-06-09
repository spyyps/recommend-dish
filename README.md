# 环球美食推荐 Plugin

一个 AI agent 插件：当用户表达就餐意向（「推荐晚餐」「不知道吃什么」「想吃点辣的」），基于 396 道菜的全球美食知识库做加权随机推荐。

- **零依赖**：纯 Python 3 标准库
- **跨 agent**：Claude Code（plugin）+ Gemini CLI（GEMINI.md）+ 任何 MCP 兼容 agent（规划中）
- **智能兜底**：本地知识库 → 自动放宽 → 网络搜索 → LLM 常识，4 层兜底
- **去偏置 + 多样性**：避免大菜系（如中餐）压制小菜系；避免推荐 3 道全是同一菜系

## 快速测试

```bash
python3 scripts/recommender.py --count 3 --keywords "辣,牛肉"
```

返回 JSON：

```json
{"dishes": [{"id": "...", "name": "麻婆豆腐", "price": 38, "cuisine": "川菜", ...}, ...], "exhausted": false, ...}
```

完整参数：

```bash
python3 scripts/recommender.py --help
```

## 安装到不同 AI Agent

### Claude Code

**方式 A：自建 marketplace（推荐）**

```
/plugin marketplace add spyyps/recommend-dish
/plugin install menus-recommender@spyyps-recommend-dish
```

安装后在任意目录的 Claude Code 会话里说「推荐晚餐」「想吃点辣的」即可触发。
后续更新插件：`/plugin update menus-recommender`。

**方式 B：本地 git clone**

```bash
git clone https://github.com/spyyps/recommend-dish ~/.claude/plugins/menus-recommender
```

### Gemini CLI

```bash
git clone https://github.com/spyyps/recommend-dish
cd recommend-dish
gemini   # 在本目录运行 Gemini CLI，会自动加载 GEMINI.md
```

### Cursor / Codex

待添加（参考 `.cursor-plugin/` 与 `.codex-plugin/` 的多 manifest 适配，第二阶段交付）。

### MCP 兼容的任意 Agent

待添加（第二阶段交付 `mcp-server/` 目录，发布到 npm 与 Docker Hub）。

## 触发示例

| 用户说 | 触发 | 解析为 |
|--------|------|--------|
| 「推荐晚餐」 | ✓ | 默认 3 道，无筛选 |
| 「想吃点辣的」 | ✓ | `--keywords "辣"` |
| 「来 5 道便宜的海鲜」 | ✓ | `--count 5 --keywords "海鲜" --price-tier "实惠"` |
| 「推荐两道川菜」 | ✓ | `--count 2 --cuisine "川菜"` |
| 「换一批」（紧接上一次推荐） | ✓ | `--exclude-ids "<上轮所有 id>"` |
| 「100 块以内的欧洲菜」 | ✓ | `--max-price 100 --geo "欧洲"` |

## 算法核心

1. **关键词硬过滤**：用户传了关键词时，菜品必须至少命中一个（OR 语义）
2. **多重命中加权**：命中 N 个关键词的菜，权重 ×2^(N-1)
3. **菜系反偏置**：权重 ×1/√(该菜系总菜数)，平衡中餐占 35% 的天然偏差
4. **多样性贪心**：同一菜系上限 ≤ ceil(count/3)
5. **价格档松弛**：候选不足自动去掉价格档重试一次

## 关键词白名单

只接受以下关键词，超出范围的（如「不辣」「清淡」）由 LLM 在调用前消化掉：

- **口味**：麻辣 / 辣 / 甜 / 酸 / 咸 / 鲜
- **食材**：海鲜 / 牛肉 / 羊肉 / 猪肉 / 鸡肉 / 素食
- **类型**：面食 / 米饭类 / 汤 / 甜品 / 烧烤 / 火锅 / 咖喱 / 汉堡披萨 / 饮品

## 数据来源

- 全球菜系 396 道菜（10 个地区、40+ 菜系、67 个子风味）
- 价格范围 ¥6 ~ ¥388（CNY）
- 完整数据见 `menu.json` 与 `knowledge_base/` 各索引文件

## 发布到他人（仓库 owner 视角）

### 作为 Plugin 分享

1. `git push` 到 GitHub（本仓库已就绪：`spyyps/recommend-dish`）
2. 仓库内 `.claude-plugin/marketplace.json` 已配置好，列出所有可装插件
3. 在 README 贴出一行安装命令，分享仓库链接即可

### 作为 MCP 分享（第二阶段）

仓库内会增加 `mcp-server/` 目录，复用同一个 `recommender.py`。发布方式：

- **npm**：`npm publish @spyyps/menus-mcp` → 用户配 `npx -y @spyyps/menus-mcp`
- **MCPB 单文件**：`npx @anthropic-ai/mcpb pack` → GitHub Release → 拖入 Claude Desktop
- **Docker**：`docker push spyyps/menus-mcp` → 用户配 `docker run`
- **社区目录**：提 PR 到 `github.com/modelcontextprotocol/servers`

## 许可

MIT
