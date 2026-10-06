<h1 align="center">Rules Hub</h1>

<p align="center"><a href="https://github.com/Ethereal-09/rules-hub/actions/workflows/merge.yml"><img src="https://img.shields.io/badge/Actions-手动触发合并-blue?style=for-the-badge&logo=github"></a></p>

<h3 align="center">个人自用规则订阅 · 合并上游规则 · 多平台转换</h3>

<p align="center">每个平台独立合并上游规则并去重。规则内容由上游作者维护。</p>

上次更新时间：2026-10-07 05:04:42

## 订阅地址

### AdGuard Home

> 详细统计见 [STATS.md](adguard/dist/STATS.md)。

| 规则类型 | 规则数 | 原始链接 | 加速 1 | 加速 2 |
|---|---|---|---|---|
| 黑名单（拦截） | 220,181 | [订阅](https://raw.githubusercontent.com/Ethereal-09/rules-hub/main/adguard/dist/adguard-black.txt) | [Boki](https://github.boki.moe/https://raw.githubusercontent.com/Ethereal-09/rules-hub/main/adguard/dist/adguard-black.txt) | [ghfast](https://ghfast.top/https://raw.githubusercontent.com/Ethereal-09/rules-hub/main/adguard/dist/adguard-black.txt) |
| 白名单（放行） | 15,223 | [订阅](https://raw.githubusercontent.com/Ethereal-09/rules-hub/main/adguard/dist/adguard-white.txt) | [Boki](https://github.boki.moe/https://raw.githubusercontent.com/Ethereal-09/rules-hub/main/adguard/dist/adguard-white.txt) | [ghfast](https://ghfast.top/https://raw.githubusercontent.com/Ethereal-09/rules-hub/main/adguard/dist/adguard-white.txt) |

> 订阅地址如被墙，可选加速链接（Boki / ghfast）。

## 目录结构

```
rules-hub/
├── adguard/                 # AdGuard Home 规则
│   ├── black-sources.txt    # 黑名单源（一行一个 URL）
│   ├── white-sources.txt    # 白名单源（一行一个 URL）
│   ├── my-blacklist.txt     # 我的黑名单（一行一个裸域名）
│   ├── my-whitelist.txt     # 我的白名单（一行一个裸域名）
│   ├── merge.py             # 合并脚本
│   └── dist/                # 输出（Actions 自动生成，勿手改）
│       ├── adguard-black.txt
│       ├── adguard-white.txt
│       └── STATS.md
└── .github/workflows/merge.yml   # 自动合并工作流（自动发现所有规则目录）
```

## 修改上游源

编辑对应平台的 `black-sources.txt` / `white-sources.txt`，`#` 开头为注释。
push 后自动触发一次合并。

## 我的规则（my-blacklist.txt / my-whitelist.txt）

一行一个裸域名，脚本自动转成本平台格式：

| 你写进 `my-blacklist.txt` | 输出 |
|---|---|
| `ads.example.com` | `\|\|ads.example.com^` |

| 你写进 `my-whitelist.txt` | 输出 |
|---|---|
| `good.example.com` | `@@\|\|good.example.com^` |

- **黑白源分离**：黑名单源、白名单源各自独立文件
- **合并规则**：丢弃注释（`!`）、元数据（`[...]`）；大写转小写再整行去重
- **不做对冲**：黑白规则可能并存，交给引擎运行时裁决

## 当前上游源（adguard）

### 黑名单源（black-sources.txt）

| 源 | 分类 |
|---|---|
| [AdGuard Base](https://github.com/AdguardTeam/FiltersRegistry) | 通用广告（官方） |
| [AdGuard Chinese](https://github.com/AdguardTeam/FiltersRegistry) | 中文广告（官方） |
| [EasyList](https://easylist.to/) | 英文通用（老牌） |
| [EasyList China](https://easylist.to/) | 中文通用（老牌） |
| [EasyPrivacy](https://easylist.to/) | 隐私追踪 |
| [xinggsf/Adblock-Plus-Rule](https://github.com/xinggsf/Adblock-Plus-Rule) | 国内视频去广告 |
| [cjx82630/cjxlist](https://github.com/cjx82630/cjxlist) | 国内 annoyances |
| [Noyllopa/NoAppDownload](https://github.com/Noyllopa/NoAppDownload) | 阻止 App 下载跳转 |
| [TG-Twilight/AWAvenue-Ads-Rule](https://github.com/TG-Twilight/AWAvenue-Ads-Rule) | 广告/隐私/不受欢迎 |
| [perflyst/SmartTV-AGH](https://github.com/perflyst/PiHoleBlocklist) | 智能电视 |
| [sjhgvr/oisd abp_small](https://github.com/sjhgvr/oisd) | 大而全（ABP 版） |

### 白名单源（white-sources.txt）

| 源 | 分类 |
|---|---|
| [AdGuard Chinese allowlist](https://github.com/AdguardTeam/AdguardFilters) | 中文站误杀修复 |
| [AdGuard German allowlist](https://github.com/AdguardTeam/AdguardFilters) | 德文站误杀修复 |
| [AdGuard Turkish allowlist](https://github.com/AdguardTeam/AdguardFilters) | 土耳其站误杀修复 |
| [AdGuard Spyware allowlist](https://github.com/AdguardTeam/AdguardFilters) | 反误报 |

## 支持的平台（计划）

| 平台 | 目录 | 状态 |
|---|---|---|
| AdGuard Home | `adguard/` | ✅ 已完成 |
| mihomo / Clash | `mihomo/` | ⏳ 计划中 |
| Surge | `surge/` | ⏳ 计划中 |
| Quantumult X | `qx/` | ⏳ 计划中 |
| dnsmasq | `dnsmasq/` | ⏳ 计划中 |
| Pi-hole / hosts | `pihole/` | ⏳ 计划中 |
| SmartDNS | `smartdns/` | ⏳ 计划中 |
| Shadowrocket | `shadowrocket/` | ⏳ 计划中 |
