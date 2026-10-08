# Quantumult X 懒人配置流水线

底包：`https://ddgksf2013.top/Profile/QuantumultX.conf`。

每天北京时间 06:25 运行独立 GitHub Actions：拉取实时底包，把原底包开头的作者专用说明和更新日志替换为本仓库简洁配置头（保留底包来源及作者署名），不改 `[general]` 及其后面的功能配置；仅下载已启用的 `[filter_remote]`、`[rewrite_remote]`，并解析活动重写规则中的 `script-request/response-*`、`script-path`、`script-url`，以及 `[task_local]` 的交互脚本、`[general]` 的资源解析器；这些功能性依赖保存到 `assets/filter/`、`assets/rewrite/`、`assets/script/`，成功镜像的 URL 改为本仓库 Raw 地址，生成 `dist/QuantumultX.conf`。不扫描 blackmatrix7 全目录、不额外开启规则，也不改 `rules-hub/qx/`。

推送并完成首次 Actions 构建后，QX「下载配置」地址：

`https://raw.githubusercontent.com/Ethereal-09/rules-hub/main/Quantumult/dist/QuantumultX.conf`

```text
Quantumult/
├── dist/QuantumultX.conf
├── assets/
│   ├── filter/      # 已启用的分流
│   ├── rewrite/     # 已启用的重写
│   └── script/      # 重写依赖、任务、资源解析器
└── SOURCES.md       # 自动生成：文件 → 原地址 → SHA-256
```

目录只按用途分三级，不按来源另建文件夹；同名文件使用原 URL 的短哈希消歧。`SOURCES.md` 在每次构建时重新生成，只列出本次成功镜像并引用的文件。

## QX 广告分流上游

`Quantumult/convert_ads.py` 从 `adguard/dist/adguard-black.txt` 提取纯域名拦截（`$important` 优先级不带到 QX），结合可识别白名单例外排除，再与 [`ads-sources.txt`](ads-sources.txt) 中的 QX 原生广告分流源合并去重。目前已配置 Cats-Team/AdRules 的 `qx.conf`。输出 `Quantumult/dist/Quantumult-ads.list` 与 `Quantumult-ads-STATS.md`；`merge.yml` 在 AdGuard 合并完成后执行，推送冲突重算时也执行。此独立订阅**不自动加进完整 QX 配置**；底包若同时启用 Cats-Team，会出现客户端层面的重复拦截。

## 邮件通知

工作流构建及发布完成后（成功或失败均会尝试发送），使用仓库已有的 Actions Secrets：`SMTP_USER`、`SMTP_PASS`、`SMTP_TO`，通过 163 SMTP 发送结果、镜像统计和运行记录链接。未设置 Secrets 时跳过通知；邮件发送失败会在 Actions 日志中报错，但不会把已成功的构建改判为失败。统计中的“下载失败”表示该资源保留了原上游链接，不代表本次 Actions 必然失败。

## 注意

- 仅镜像已启用规则及可识别的静态功能依赖；不镜像图标、测速地址、证书、节点订阅或带凭证 URL。重写 JS 运行时动态请求、混淆代码里的隐藏依赖无法仅靠静态解析保证穷尽。下载失败保留原地址并告警，不能把部分成功宣称为全部镜像完成。
- HTTPS URL 若带查询参数或疑似凭证路径则跳过镜像，避免私密链接出现在公开仓库。请不要把私人节点订阅添加到公开底包。
- 镜像文件保留旧版本已有的文件名，避免 QX 客户端短时间内引用失效；上游删除的项目不会出现在新配置中，但旧镜像文件暂不自动删除。
- 已镜像的重写内部脚本 URL 会指向本仓库；未镜像成功的仍依赖上游，MITM 的效果与安全性仍取决于规则内容。首次导入前请备份 QX 当前配置。
- 本目录不复用 `qx-config-sync` 代码。当前尚未设计个人增量覆盖机制；你明确指定具体改动后再加，避免擅改底包。

本地运行：`python3 Quantumult/build.py`。测试：`python3 -m unittest discover -s Quantumult -p 'test_*.py' -v`。`--base-file` 可使用本地底包做离线测试。
