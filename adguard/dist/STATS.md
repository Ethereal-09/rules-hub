# 合并统计

- 生成时间：2026-10-22 10:36:39
- 上游源：7 个（成功 7，失败 0）
- 黑名单规则：**266978** 条（去重 88383）
- 白名单规则：**32** 条（去重 0）
- 非 DNS 规则已跳过：2044 行（含注释/元数据）
- 筛选范围：黑名单仅纯域名拦截（含 `$important`）；白名单保留白源全部非注释规则与黑源 `@@` 例外，仅去重，可能含非放行规则。

| 上游源 | 读取 | 新增黑 | 新增白 | 状态 |
|---|---|---|---|---|
| https://raw.githubusercontent.com/damengzhu/banad/main/jiekouAD.txt | 5908 | 4511 | 32 | OK |
| https://raw.githubusercontent.com/TG-Twilight/AWAvenue-Ads-Rule/main/AWAvenue-Ads-Rule.txt | 973 | 961 | 0 | OK |
| https://raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/pro.mini.txt | 80317 | 80303 | 0 | OK |
| https://abp.oisd.nl/basic | 58313 | 58302 | 0 | OK |
| https://raw.githubusercontent.com/Cats-Team/AdRules/main/dns.txt | 210286 | 209840 | 0 | OK |
| https://raw.githubusercontent.com/AdguardTeam/AdguardFilters/master/MobileFilter/sections/adservers.txt | 1066 | 901 | 0 | OK |
| https://raw.githubusercontent.com/rssvcn/qy-Ads-Rule/main/black.txt | 574 | 543 | 0 | OK |

