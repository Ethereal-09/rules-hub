# 合并统计

- 生成时间：2026-10-10 06:45:51
- 上游源：8 个（成功 8，失败 0）
- 黑名单规则：**260901** 条（去重 83739）
- 白名单规则：**32** 条（去重 0）
- 非 DNS 规则已跳过：3301 行（含注释/元数据）
- 筛选范围：黑名单仅纯域名拦截（含 `$important`）；白名单保留白源全部非注释规则与黑源 `@@` 例外，仅去重，可能含非放行规则。

| 上游源 | 读取 | 新增黑 | 新增白 | 状态 |
|---|---|---|---|---|
| https://raw.githubusercontent.com/damengzhu/banad/main/jiekouAD.txt | 5906 | 4510 | 32 | OK |
| https://raw.githubusercontent.com/TG-Twilight/AWAvenue-Ads-Rule/main/AWAvenue-Ads-Rule.txt | 973 | 961 | 0 | OK |
| https://raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/pro.mini.txt | 67134 | 67120 | 0 | OK |
| https://abp.oisd.nl/basic | 57860 | 57849 | 0 | OK |
| https://raw.githubusercontent.com/Cats-Team/AdRules/main/dns.txt | 201423 | 200977 | 0 | OK |
| https://raw.githubusercontent.com/AdguardTeam/AdguardFilters/master/MobileFilter/sections/adservers.txt | 1065 | 900 | 0 | OK |
| https://raw.githubusercontent.com/rssvcn/qy-Ads-Rule/main/black.txt | 574 | 543 | 0 | OK |
| https://raw.githubusercontent.com/2771936993/HG/main/hg1.txt | 13038 | 11780 | 0 | OK |

