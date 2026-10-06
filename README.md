<h1 align="center">Rules Hub</h1>

<p align="center">
  <a href="https://github.com/Ethereal-09/rules-hub/actions/workflows/merge.yml"><img src="https://img.shields.io/badge/Actions-自动合并-blue?style=for-the-badge&logo=github"></a>
  <img src="https://img.shields.io/badge/平台-AdGuard%20Home-brightgreen?style=for-the-badge">
  <img src="https://img.shields.io/badge/更新-每%208%20小时-orange?style=for-the-badge">
</p>

<p align="center">合并上游规则，转换为多平台可用的规则订阅。</p>

<p align="center"><sub>上次更新：2026-10-07 05:31:25

---

## 📥 订阅地址

### AdGuard Home

| 类型 | 规则数 | 原始 | 加速 1 | 加速 2 |
|---|---|---|---|---|
| **黑名单（拦截）** | 220,193 | [复制](https://raw.githubusercontent.com/Ethereal-09/rules-hub/main/adguard/dist/adguard-black.txt) | [Boki](https://github.boki.moe/https://raw.githubusercontent.com/Ethereal-09/rules-hub/main/adguard/dist/adguard-black.txt) | [ghfast](https://ghfast.top/https://raw.githubusercontent.com/Ethereal-09/rules-hub/main/adguard/dist/adguard-black.txt) |
| **白名单（放行）** | 15,223 | [复制](https://raw.githubusercontent.com/Ethereal-09/rules-hub/main/adguard/dist/adguard-white.txt) | [Boki](https://github.boki.moe/https://raw.githubusercontent.com/Ethereal-09/rules-hub/main/adguard/dist/adguard-white.txt) | [ghfast](https://ghfast.top/https://raw.githubusercontent.com/Ethereal-09/rules-hub/main/adguard/dist/adguard-white.txt) |

> 直连被墙时用加速链接 · 详细统计见 [STATS.md](adguard/dist/STATS.md)

---

## 🧩 支持的平台

| 平台 | 目录 | 状态 |
|---|---|---|
| AdGuard Home | `adguard/` | ✅ |
| mihomo / Clash | `mihomo/` | ⏳ |
| Surge | `surge/` | ⏳ |
| Quantumult X | `qx/` | ⏳ |
| dnsmasq | `dnsmasq/` | ⏳ |
| Pi-hole / hosts | `pihole/` | ⏳ |
| SmartDNS | `smartdns/` | ⏳ |
| Shadowrocket | `shadowrocket/` | ⏳ |

每个平台独立目录、独立源、独立合并，互不影响。

---

## 📂 目录结构

```
rules-hub/
├── adguard/                  # AdGuard Home
│   ├── black-sources.txt     # 黑名单源（一行一个 URL）
│   ├── white-sources.txt     # 白名单源（一行一个 URL）
│   ├── my-blacklist.txt      # 我的黑名单（一行一个裸域名）
│   ├── my-whitelist.txt      # 我的白名单（一行一个裸域名）
│   ├── merge.py              # 合并脚本
│   └── dist/                 # 输出（自动生成，勿手改）
└── .github/workflows/        # 自动合并工作流
```

---

## ⚙️ 合并规则

- **黑名单** = 上游黑名单源【合并 + 去重】+ 我的黑名单
- **白名单** = 上游白名单源【合并 + 去重】+ 黑源里筛出的白名单 + 我的白名单
- 丢弃注释（`!`）、元数据（`[...]`）
- **统一转小写，再整行去重**
- 不做对冲 —— 黑白可能并存，交给引擎运行时裁决

---

## ✏️ 我的规则

`my-blacklist.txt` / `my-whitelist.txt` 里**一行一个裸域名**，脚本自动转换：

| 文件 | 写法 | 输出 |
|---|---|---|
| `my-blacklist.txt` | `ads.example.com` | `\|\|ads.example.com^` |
| `my-whitelist.txt` | `good.example.com` | `@@\|\|good.example.com^` |

修改上游源：编辑对应平台的 `black-sources.txt` / `white-sources.txt`，`#` 开头为注释，push 后自动触发合并。

---

## 📚 当前上游源

<details>
<summary><b>AdGuard Home · 黑名单源（11）</b></summary>

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

</details>

<details>
<summary><b>AdGuard Home · 白名单源（4）</b></summary>

| 源 | 分类 |
|---|---|
| [AdGuard Chinese allowlist](https://github.com/AdguardTeam/AdguardFilters) | 中文站误杀修复 |
| [AdGuard German allowlist](https://github.com/AdguardTeam/AdguardFilters) | 德文站误杀修复 |
| [AdGuard Turkish allowlist](https://github.com/AdguardTeam/AdguardFilters) | 土耳其站误杀修复 |
| [AdGuard Spyware allowlist](https://github.com/AdguardTeam/AdguardFilters) | 反误报 |

</details>
