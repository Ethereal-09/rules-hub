# 上游规则来源

本仓库所有规则均由下列公开上游源合并、去重后生成，仅做格式转换，**不对规则内容做审查**。
各上游规则的版权归其作者所有，使用前请自行确认各源的授权条款。

最后核对：2026-10-10

---

## AdGuard Home

### 黑名单源（8）

| 源 | 说明 |
|:---|:---|
| [damengzhu/banad · jiekouAD.txt](https://github.com/damengzhu/banad) | 国内接口广告 |
| [TG-Twilight/AWAvenue-Ads-Rule](https://github.com/TG-Twilight/AWAvenue-Ads-Rule) | 广告 / 隐私 / 不受欢迎 |
| [hagezi/dns-blocklists · pro.mini](https://github.com/hagezi/dns-blocklists) | 综合 DNS 拦截（精简专业版） |
| [oisd.nl · basic](https://oisd.nl/) | 大而全 DNS 拦截（基础版） |
| [Cats-Team/AdRules · dns.txt](https://github.com/Cats-Team/AdRules) | 中文区广告与追踪 |
| [AdguardTeam/AdguardFilters · MobileFilter/adservers](https://github.com/AdguardTeam/AdguardFilters) | 移动端广告服务器（官方） |
| [rssvcn/qy-Ads-Rule · black.txt](https://github.com/rssvcn/qy-Ads-Rule) | 中文广告 |
| [2771936993/HG · hg1.txt](https://github.com/2771936993/HG) | 综合拦截 |

### 白名单源（0）

当前未配置独立白源。白名单由**黑源中的 `@@` 例外**与 `adguard/my-whitelist.txt` 生成。

> 说明：AdGuard 官方 allowlist 属于客户端过滤器语法（含路径、页面元素规则），
> 无法在 AdGuard Home 的 DNS 层按原意执行，故未纳入。

---

## Quantumult X

### 配置底包

| 来源 | 说明 |
|:---|:---|
| [ddgksf2013.top/Profile/QuantumultX.conf](https://ddgksf2013.top/Profile/QuantumultX.conf) | 墨鱼 QX 懒人配置底包（作者 @ddgksf2013） |

### 追加重写（AdBlock）

均来自 [ddgksf2013/Rewrite](https://github.com/ddgksf2013/Rewrite)：

| 配置 | 说明 |
|:---|:---|
| `Applet.conf` | 微信小程序去广告 |
| `BiliBiliComicsAds.conf` | 哔哩哔哩漫画净化 |
| `BingSimplify.conf` | Bing 首页简化 |
| `CainiaoAds.conf` | 菜鸟净化 |
| `CheLaiLeAds.conf` | 车来了净化 |
| `ChinaUnicomAds.conf` | 中国联通净化 |
| `FakeiOSAds.conf` | iOS 伪装影视 APP 净化 |
| `KeepAds.conf` | Keep 应用净化 |
| `MoJiWeatherAds.conf` | 墨迹天气净化 |
| `NeteaseMailAds.conf` | 网易邮箱大师净化 |
| `QiShuiMusicAds.conf` | 汽水音乐净化 |
| `RedditAds.conf` | Reddit 增强 |
| `SmzdmAds.conf` | 什么值得买净化 |
| `TaoPiaoPiaoAds.conf` | 淘票票净化 |
| `TieBaAds.conf` | 百度贴吧净化 |
| `XiaoYuZhouAds.conf` | 小宇宙 FM 去广告 |
| `Ximalaya.conf` | 喜马拉雅净化 |

### 广告分流

| 来源 | 说明 |
|:---|:---|
| [Cats-Team/AdRules · qx.conf](https://github.com/Cats-Team/AdRules) | QX 原生广告分流 |
| 本仓库 AdGuard 黑名单 | 由 DNS 域名规则转换而来 |

### 图标

| 来源 | 说明 |
|:---|:---|
| [Koolson/Qure](https://github.com/Koolson/Qure) | 策略组图标（IconSet/Color、IconSet/mini） |
| [Orz-3/mini](https://github.com/Orz-3/mini) | 补充图标 |

---

## 镜像与产物

| 文件 | 说明 |
|:---|:---|
| [`adguard/dist/STATS.md`](adguard/dist/STATS.md) | AdGuard 合并统计 |
| [`Quantumult/SOURCES.md`](Quantumult/SOURCES.md) | QX 镜像清单：本仓库文件 → 原地址 → SHA-256 |

---

> 免责声明：本仓库为个人自用的规则合集，仅供学习与研究使用。
> 所有规则按「现状」提供，不附带任何明示或暗示的担保。
> 使用本仓库规则所产生的任何直接或间接后果，由使用者自行承担。
> 若上游作者认为本仓库的使用方式不当，请通过 Issue 联系，我们会及时调整或移除。
