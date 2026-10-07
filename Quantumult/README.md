# Quantumult X 懒人配置流水线

底包：`https://ddgksf2013.top/Profile/QuantumultX.conf`。

每天北京时间 06:25 运行独立 GitHub Actions：拉取实时底包，**只下载底包中已启用**的 `[filter_remote]` 与 `[rewrite_remote]` URL，保存到 `assets/filter/`、`assets/rewrite/`，并将这些 URL 改写为本仓库 Raw 地址，生成 `dist/QuantumultX.conf`。不扫描 blackmatrix7 全目录、不额外开启规则，也不改 `rules-hub/qx/`。原底包其他部分按原样保留，包括策略、MITM、脚本引用、节点区块。

推送并完成首次 Actions 构建后，QX「下载配置」地址：

`https://raw.githubusercontent.com/Ethereal-09/rules-hub/main/Quantumult/dist/QuantumultX.conf`

## 注意

- 仅镜像**启用的远程分流与远程重写文件**，不镜像重写内部引用的 JS 脚本、其它远程附件，也不复制节点订阅或私密 URL。下载失败保留原地址并告警，保证不会指向不存在的镜像。
- HTTPS URL 若带查询参数或疑似凭证路径则跳过镜像，避免私密链接出现在公开仓库。请不要把私人节点订阅添加到公开底包。
- 镜像文件保留旧版本已有的文件名，避免 QX 客户端短时间内引用失效；上游删除的项目不会出现在新配置中，但旧镜像文件暂不自动删除。
- 原样保留底包的远程重写意味着其中的脚本和 MITM 效果及安全性取决于上游；首次导入前请备份 QX 当前配置。
- 本目录不复用 `qx-config-sync` 代码。当前尚未设计个人增量覆盖机制；你明确指定具体改动后再加，避免擅改底包。

本地运行：`python3 Quantumult/build.py`。测试：`python3 -m unittest discover -s Quantumult -p 'test_*.py' -v`。`--base-file` 可使用本地底包做离线测试。
