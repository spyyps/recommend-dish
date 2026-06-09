# 环球美食菜单 AI 知识库

> 基于 menu.json 拆分，方便 AI 按多种维度快速查询菜品与菜系信息。

## 文件结构

```
knowledge_base/
├── README.md                  ← 本文件（总索引）
├── kb_hierarchy.json          ← 层级树：地区 > 菜系 > 子风味 > 菜品ID列表
├── kb_dish_index.json         ← 扁平菜品索引（376道），按 id 列出完整信息
├── kb_keyword_index.json      ← 关键词反向索引：关键词 → 菜品ID列表
├── kb_price_index.json        ← 价格分档索引：经济/实惠/中档/高档/奢华
├── kb_cuisine_index.json      ← 菜系索引：菜系名 → 菜品列表
└── by_region/                 ← 按地区拆分的 Markdown 文件（人类/AI 均可读）
    ├── asia_china.md          ← 中华料理（八大菜系+地方风味）
    ├── asia_east.md           ← 东亚料理（日本/韩国/蒙古）
    ├── asia_se.md             ← 东南亚料理（泰国/越南/新马印/菲律宾/缅柬）
    ├── asia_south.md          ← 南亚料理（印度/斯里兰卡/巴基斯坦）
    ├── middle_east.md         ← 中东·西亚·中亚
    ├── africa.md              ← 非洲料理（北非/西非/东非/南非）
    ├── europe_south.md        ← 欧洲料理（意/法/西/英/德/希腊/北欧/东欧）
    ├── americas.md            ← 美洲料理（美国/墨西哥/拉美/加勒比）
    ├── oceania.md             ← 大洋洲（澳洲/新西兰/太平洋岛国）
    └── world_fusion.md        ← 饮品与甜品（全球）
```

## 查询方式

### 1. 按菜品名/ID 查询
读取 `kb_dish_index.json`，按 `id` 或 `name`/`name_en` 字段匹配。

### 2. 按地区/菜系浏览
读取 `by_region/` 下对应地区的 Markdown 文件，包含完整菜品信息和描述。

### 3. 按关键词搜索
读取 `kb_keyword_index.json`，按关键词获取菜品 ID 列表，再从 `kb_dish_index.json` 获取详情。

支持的关键词类别：
- 口味：麻辣、辣、甜、酸、鲜
- 食材：海鲜、牛肉、羊肉、猪肉、鸡肉
- 类型：面食、米饭类、汤、甜品、烧烤、火锅、素食、咖喱、汉堡披萨、饮品

### 4. 按价格区间筛选
读取 `kb_price_index.json`：
- 经济 (≤20元): 54 道
- 实惠 (21-50元): 220 道
- 中档 (51-100元): 82 道
- 高档 (101-200元): 18 道
- 奢华 (>200元): 2 道

### 5. 按菜系查询
读取 `kb_cuisine_index.json`，按菜系名获取该菜系所有菜品。

### 6. 了解层级结构
读取 `kb_hierarchy.json`，获取完整的 地区 → 菜系 → 子风味 → 菜品ID 树。

## 统计

| 维度 | 数量 |
|------|------|
| 地区 | 10 |
| 菜系 | 40 |
| 子风味 | 67 |
| 菜品总数 | 376 |
| 价格区间 | ¥8 ~ ¥388 |
