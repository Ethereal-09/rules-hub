# AdGuard → QX 广告分流转换与上游合并统计

- black_input: 254027
- converted: 254025
- excluded: 2
- source_added: 1
- source_allow_excluded: 1
- source_duplicate: 203855
- source_valid: 203856
- sources_ok: 1
- unique_allow: 4
- unique_black: 254027
- white_ambiguous: 28
- white_input: 32

AdGuard 纯域名转换后与 `ads-sources.txt` 中的 QX 原生 HOST-SUFFIX/REJECT 上游去重。白名单只从 AdGuard 转换候选中排除，不生成 DIRECT。
