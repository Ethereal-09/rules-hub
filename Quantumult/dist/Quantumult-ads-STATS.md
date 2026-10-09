# AdGuard → QX 广告分流转换与上游合并统计

- black_input: 115441
- converted: 115437
- excluded: 4
- source_added: 96170
- source_duplicate: 102502
- source_valid: 198672
- sources_ok: 1
- unique_allow: 48
- unique_black: 115441
- white_ambiguous: 12059
- white_input: 12107

AdGuard 纯域名转换后与 `ads-sources.txt` 中的 QX 原生 HOST-SUFFIX/REJECT 上游去重。白名单只从 AdGuard 转换候选中排除，不生成 DIRECT。
