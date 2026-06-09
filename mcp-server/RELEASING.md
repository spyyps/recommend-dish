# PyPI 发布检查清单（menus-mcp）

发布前在仓库根目录 / mcp-server/ 目录依次操作。涉及到 PyPI 凭证的步骤需要使用 owner 本人的 token，本文件不存任何 secret。

## 0. 一次性准备

1. PyPI 账号 + 启用 2FA：https://pypi.org/account/register/
2. 生成 API token（scope 限制到 `menus-mcp` 项目，首次上传时只能选 "Entire account"，后续可缩窄）
3. 本机写入 `~/.pypirc`（权限 600）：

   ```ini
   [pypi]
   username = __token__
   password = pypi-<your-token>

   [testpypi]
   username = __token__
   password = pypi-<your-testpypi-token>
   ```

4. 安装构建工具（任选其一）：
   - `uv`（已用过）：自带 `uv build`，无需 pip
   - 或 `pip install --user build twine`

## 1. 发版前自检

- [ ] `git status` 干净（无未提交改动）
- [ ] `git pull --rebase` 与 main 同步
- [ ] `mcp-server/pyproject.toml` 的 `version` 已按 [SemVer](https://semver.org/lang/zh-CN/) 加号
  - 修 bug → patch（1.0.0 → 1.0.1）
  - 加工具/参数（向后兼容）→ minor（1.0.1 → 1.1.0）
  - 改工具名/参数语义（破坏兼容）→ major（1.1.0 → 2.0.0）
- [ ] 在 main 上跑端到端：
  ```bash
  python3 scripts/recommender.py --count 3 --keywords "辣"
  ```
- [ ] symlink 仍然存在（`ls -l mcp-server/menus_mcp/`）

## 2. 构建

```bash
cd mcp-server
rm -rf dist build *.egg-info menus_mcp.egg-info
uv build                          # 或 python3 -m build
ls -lh dist/                      # 应该有 .tar.gz 与 .whl 各一份
```

- [ ] wheel 体积合理（当前 ~74KB）
- [ ] 抽样验证 wheel 内容（symlink 已解析为真实文件）：
  ```bash
  unzip -l dist/menus_mcp-*.whl | grep -E '(recommender|knowledge_base)'
  ```

## 3. 本地烟测 wheel

```bash
# 用 uvx 从本地 wheel 拉起 server
python3 /tmp/mcp_smoke2.py uvx --from ./dist/menus_mcp-*.whl menus-mcp
```

期望看到三行响应：`id=1` server info、`id=2` 列出两个 tools、`id=3` 返回菜品列表。

## 4. 先发 TestPyPI（建议）

```bash
uv publish --publish-url https://test.pypi.org/legacy/ dist/*
# 或：twine upload -r testpypi dist/*
```

然后用 uvx 从 testpypi 拉一次：

```bash
uvx --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    menus-mcp < /dev/null
# Ctrl+C 退出即可，能启动不报错就算 OK
```

## 5. 正式发布

```bash
uv publish dist/*                 # 或：twine upload dist/*
```

成功后页面：https://pypi.org/project/menus-mcp/

## 6. 发版后

- [ ] 打 git tag：
  ```bash
  git tag v$(grep '^version' mcp-server/pyproject.toml | cut -d'"' -f2)
  git push --tags
  ```
- [ ] 在 GitHub 上创建 Release，note 写本次变更
- [ ] 用户侧验证：
  ```bash
  uvx menus-mcp < /dev/null     # 能起即算成功
  ```
- [ ] 可选：到 [`modelcontextprotocol/servers`](https://github.com/modelcontextprotocol/servers) 提 PR 把 menus-mcp 加进社区目录

## 失败回滚

PyPI **不允许覆盖同版本号**。如果某版本发错了：

1. 不要试图删 + 重传同号 — 删了也不能再用同号
2. 在 PyPI 上把出错版本 `Yank`（保留链接但不再被新安装解析）
3. 升一位 patch 号（1.0.1 → 1.0.2），修完后重新发布

## 常用诊断

- uvx 报 `No solution found` → 检查 `requires-python` 与本地 Python 版本是否匹配
- wheel 缺数据文件 → 检查 `pyproject.toml` 的 `[tool.setuptools.package-data]`
- symlink 在 wheel 里变成 0 字节文本 → 用 `uv build` 而非自定义打包脚本；setuptools 默认会解析 symlink
