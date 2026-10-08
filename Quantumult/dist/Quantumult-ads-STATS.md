# AdGuard → QX 广告分流转换与上游合并统计

- black_input: 115346
- converted: 115342
- excluded: 4
- source_added: 96152
- source_duplicate: 102263
- source_valid: 198415
- sources_ok: 1
- unique_allow: 48
- unique_black: 115346
- white_ambiguous: 12058
- white_input: 12106

AdGuard 纯域名转换后与 `ads-sources.txt` 中的 QX 原生 HOST-SUFFIX/REJECT 上游去重。白名单只从 AdGuard 转换候选中排除，不生成 DIRECT。
