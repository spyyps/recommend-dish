# menus-mcp：全球美食推荐 MCP Server

<!-- mcp-name: io.github.spyyps/menus-recommender -->

基于 396 道菜、40 个菜系的全球美食知识库做加权随机推荐。任何支持 Model Context Protocol（MCP）的 AI agent 均可使用，包括：

- [Claude Desktop](https://claude.ai/download)
- [Cline](https://github.com/cline/cline)
- [Cursor](https://cursor.sh)
- [Continue](https://continue.dev)
- 其他 MCP 兼容客户端

## 快速安装

> 也可在 [MCP Registry](https://registry.modelcontextprotocol.io/v0.1/servers?search=menus-recommender) 直接搜到本 server（`io.github.spyyps/menus-recommender`）。

### 方式 1：uvx（推荐，无需安装）

```json
{
  "mcpServers": {
    "menus": {
      "command": "uvx",
      "args": ["menus-mcp"]
    }
  }
}
```

`uvx` 会自动从 PyPI 下载并运行，首次启动稍有延迟（数据加载约 1s），后续缓存到本地。

### 方式 2：pip install

```bash
pip install menus-mcp
```

然后在 MCP 客户端配置中：

```json
{
  "mcpServers": {
    "menus": {
      "command": "menus-mcp"
    }
  }
}
```

### 方式 3：本地源码运行

```bash
git clone https://github.com/spyyps/recommend-dish
cd recommend-dish
pip install -r mcp-server/requirements.txt
# 运行入口
python3 mcp-server/server.py
# 或在 mcp-server/ 目录下：
cd mcp-server && python3 -m menus_mcp
```

然后客户端配置：

```json
{
  "mcpServers": {
    "menus": {
      "command": "python3",
      "args": ["/path/to/recommend-dish/mcp-server/server.py"]
    }
  }
}
```

## 开放的工具

### `recommend_dishes`

主推荐工具。参数（皆为可选）：

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `count` | int | 3 | 推荐数量 |
| `keywords` | str | "" | 逗号分隔的关键词（OR语义），见下方白名单 |
| `price_tier` | str | "" | 经济(≤20)/实惠(21-50)/中档(51-100)/高档(101-200)/奢华(>200) |
| `max_price` | int | 0 | 价格上限（CNY） |
| `cuisine` | str | "" | 菜系名（如「川菜」「日本料理」） |
| `geo` | str | "" | 地理大类（如「亚洲」「欧洲」） |
| `exclude_ids` | str | "" | 逗号分隔的菜品 ID，用于换一批去重 |
| `seed` | int | 0 | 随机种子（0=系统时间） |

**支持的关键词白名单：**
- 口味：麻辣、辣、甜、酸、咸、鲜
- 食材：海鲜、牛肉、羊肉、猪肉、鸡肉、素食
- 类型：面食、米饭类、汤、甜品、烧烤、火锅、咖喱、汉堡披萨、饮品

**否定注意**：用户说「不要太辣」时不要传入 `辣`——传空即可。关键词做硬过滤，传入就会强制匹配。

**返回示例（JSON）：**
```json
{
  "dishes": [
    {"id": "cn_ch_001", "name": "麻婆豆腐", "name_en": "Mapo Tofu", "price": 38, "cuisine": "川菜", "region": "中华料理", "description": "嫩豆腐配牛肉末，以花椒和豆瓣酱炒制，麻辣鲜香"}
  ],
  "exhausted": false,
  "filters": {"count": 3, "keywords": ["辣"], "price_tier": "", "relaxed": false, ...},
  "candidate_pool_size": 54,
  "returned": 3
}
```

`exhausted=true` 表示候选池不足，应触发兜底链（放宽约束、网络搜索、LLM 常识）。

### `list_keywords`

返回支持的关键词白名单。无参数。

## 兜底推荐

MCP server 仅负责第一层（本地知识库 + 加权随机）。当 `exhausted=true` 时，**应自行**按以下链兜底：

1. **降级过滤**：去掉价格约束，重试
2. **Web 搜索**：查 `"{用户原话} 推荐 菜品"`
3. **LLM 常识**：基于通用知识推荐，标注「非知识库菜品」

## 算法说明

- 关键词硬过滤：用户传关键词时菜品必须至少匹配一个（OR）
- 反偏置：`权重 × 1/√(该菜系菜品数)`，防止大菜系压制小菜系
- 多样性：同一菜系最多 ceil(count/3) 道
- 价格松弛：候选不足时自动去价格档重试一次

## 发布

```bash
cd mcp-server
pip install build
python3 -m build
twine upload dist/*
```

详见 [PyPI 发布指南](https://packaging.python.org/en/latest/tutorials/packaging-projects/)。