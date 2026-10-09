# Quantumult X 懒人配置流水线

底包：`https://ddgksf2013.top/Profile/QuantumultX.conf`。

每天北京时间 06:25 运行独立 GitHub Actions：拉取实时底包，把原底包开头的作者专用说明和更新日志替换为本仓库简洁配置头（保留底包来源及作者署名），不改 `[general]` 及其后面的功能配置；仅下载已启用的 `[filter_remote]`、`[rewrite_remote]`，并解析活动重写规则中的 `script-request/response-*`、`script-path`、`script-url`，以及 `[task_local]` 的交互脚本、`[general]` 的资源解析器；这些功能性依赖保存到 `assets/filter/`、`assets/rewrite/`、`assets/script/`，成功镜像的 URL 改为本仓库 Raw 地址，生成 `dist/QuantumultX.conf`。不扫描 blackmatrix7 全目录、不额外开启规则，也不改 `rules-hub/qx/`。

推送并完成首次 Actions 构建后，QX「下载配置」地址：

`https://raw.githubusercontent.com/Ethereal-09/rules-hub/main/Quantumult/dist/QuantumultX.conf`

```text
Quantumult/
├── build.py                # 唯一入口：构建 dist/QuantumultX.conf
├── rewrite-local.txt       # 个人追加重写（[rewrite_remote] 语法）
├── policy-local.txt        # 个人追加策略组（[policy] 语法）
├── ads-sources.txt         # QX 广告分流上游
├── lib/                    # 内部模块，不直接对外
│   ├── dependencies.py     # 重写内文 URL 改写规则
│   ├── section_inject.py   # 通用段注入器
│   ├── notify.py           # 邮件通知
│   ├── convert_ads.py      # AdGuard→QX 广告域名转换
│   └── prune_assets.py     # 陈旧镜像清理
├── tests/                  # 单元测试
├── assets/
│   ├── filter/      # 已启用的分流
│   ├── rewrite/     # 已启用的重写
│   └── script/      # 重写依赖、任务、资源解析器
├── dist/QuantumultX.conf
├── SOURCES.md       # 自动生成：文件 → 原地址 → SHA-256 + 未能镜像清单
└── .cache/          # 本地 HTTP 缓存，不提交
```

目录只按用途分三级，不按来源另建文件夹；同名文件使用原 URL 的短哈希消歧。

工作流在构建前会先跑 `tests/`（43 个用例），失败则不构建。

## 个人追加机制

底包是只读上游，无法直接修改。本流水线提供两个追加入口，在**镜像之前**注入，因此其中的资源与他人条目走完全相同的处理路径：

| 文件 | 注入位置 | 语法 |
|---|---|---|
| `rewrite-local.txt` | `[rewrite_remote]` 段尾 | `<conf URL>, tag=..., img-url=..., enabled=true` |
| `policy-local.txt` | `[policy]` 段尾 | `url-latency-benchmark=..., server-tag-regex=..., img-url=...` |

两者都由 `section_inject.py` 统一处理：定位段头、在上游条目之后、下一个段头之前插入。空文件即不追加。

## 失败处理（fail closed）

- 单条依赖下载失败 → 保留上游地址并记入 `SOURCES.md` 的「未能镜像」清单
- **失败总数超过 8 个且占比超过 8% → 构建失败，拒绝发布**（阈值可用 `QX_MAX_FAILED` / `QX_MAX_FAILED_RATIO` 覆盖）
- 底包缺失、过小、缺 `[general]`、`[general]` 之前存在活动内容 → 立即失败
- 这样避免「构建报成功、客户端却有一半规则指向不可达地址」

## 缓存与体积控制

- `download()` 使用 `ETag` / `Last-Modified` 做条件请求，命中 304 时直接读本地副本；缓存存于 `.cache/`（已 gitignore）
- JS 脚本**不做**内文 URL 改写：脚本正文是代码，同形状字符串可能是无关字面量，改写会破坏脚本
- `prune_assets.py --days 30`：构建后清理既未被当前配置引用、又超过 30 天未更新的镜像文件，避免仓库无限增长

## QX 广告分流上游

`Quantumult/convert_ads.py` 从 `adguard/dist/adguard-black.txt` 提取纯域名拦截（`$important` 优先级不带到 QX），结合可识别白名单例外排除，再与 [`ads-sources.txt`](ads-sources.txt) 中的 QX 原生广告分流源合并去重。目前已配置 Cats-Team/AdRules 的 `qx.conf`。输出 `Quantumult/dist/Quantumult-ads.list` 与 `Quantumult-ads-STATS.md`；`merge.yml` 在 AdGuard 合并完成后执行，推送冲突重算时也执行。此独立订阅**不自动加进完整 QX 配置**；底包若同时启用 Cats-Team，会出现客户端层面的重复拦截。

## 邮件通知

工作流构建及发布完成后（成功或失败均会尝试发送），使用仓库已有的 Actions Secrets：`SMTP_USER`、`SMTP_PASS`、`SMTP_TO`，通过 163 SMTP 发送结果、镜像统计、**本次触发提交的完整说明**和运行记录链接。提交说明经 GitHub API 读取，读取失败时降级为「未能读取提交说明」，不影响通知发送。

## 注意

- 仅镜像已启用规则及可识别的静态功能依赖；不镜像图标、测速地址、证书、节点订阅或带凭证 URL。重写 JS 运行时动态请求、混淆代码里的隐藏依赖无法仅靠静态解析保证穷尽。
- HTTPS URL 若带查询参数或疑似凭证路径则跳过镜像；`?raw=true` 一类无害展示参数放行。
- 镜像文件保留旧版本已有的文件名，避免 QX 客户端短时间内引用失效；上游删除的项目不会出现在新配置中，超过保留窗口的旧文件由 `prune_assets.py` 清理。
- 已镜像的重写内部脚本 URL 会指向本仓库；未镜像成功的仍依赖上游。首次导入前请备份 QX 当前配置。

本地运行：`python3 Quantumult/build.py`。清理：`python3 Quantumult/lib/prune_assets.py --days 30 --dry-run`。测试：`python3 -m unittest discover -s Quantumult/tests -t Quantumult/tests -p 'test_*.py' -v`。`--base-file` 可使用本地底包做离线测试，`--no-cache` 跳过缓存。
