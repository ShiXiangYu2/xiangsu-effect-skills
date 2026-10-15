# 像塑特效技能包备份

本仓库为本机技能资料的私有归档，采集日期：2026-10-15。

- `skills/`：当前 Codex 安装版本，优先从这里阅读。
- `packages/`：WorkBuddy 专家团完整插件、像塑内置技能、项目角色与能力模块、课程知识库、依赖工具及历史候选。内容相同的副本去重，不同版本分别保留。
- `inventory.json`：来源、逐文件原始哈希、上传内容哈希、去重映射及排除记录。
- `SHA256SUMS.json`：仓库资料文件的校验值。

这是一份归档，不会自动安装技能或覆盖工程。历史候选不等于已批准可用版本。原包保留的机器绝对路径需要在其他电脑上重新配置；维护 manifest 记录的是原本机来源，脱敏后的快照与原安装哈希可能不同。角色与能力须结合当前像塑工程手册使用。

凭据 `.env`、私钥和缓存不上传；检测出的明文密钥替换为 `REDACTED_SECRET`。完整 ZIP 包以筛查后的展开文件收录。原始教学视频和工程项目不属于本次技能包备份。原包版权和来源声明保留，不额外赋予再分发许可。

## 收录统计

- source_locations: 40
- unique_snapshots: 25
- files: 3305
- bytes: 29735120
- redacted_files: 0
- excluded_files: 4

## 包索引

|目录|文件数|
|---|---|
|skills/xiangsu-effect-editor|15|
|skills/xiangsu-effect-practitioner-lineage|48|
|skills/xiangsu-effect-workflow|99|
|skills/xiangsu-effects-production-lineage|403|
|packages/xiangsu-effect-editor--e3f81d4a7da4|14|
|packages/xiangsu-effects-production-lineage--6ca3c3c49edc|398|
|packages/previous-review-232340--39a352d29238|398|
|packages/xiangsu-effects-production-lineage--5531cf44da28|398|
|packages/xiangsu-effect-editor--250ec596ae63|6|
|packages/xiangsu-effect-editor--afb750e126fd|6|
|packages/xiangsu-effect-editor--c421f655b02c|23|
|packages/xiangsu-effect-editor--90c3baef7880|8|
|packages/xiangsu-effects-production-lineage--311d9fb16cf4|402|
|packages/baseline--62ac5a53b3e2|3|
|packages/xiangsu-effect-team--b009e1eb5cbf|104|
|packages/xiangsu-effect-team--3c9b831a290f|104|
|packages/xiangsu-effect-editor--1554b30e9ced|13|
|packages/xiangsu-effects-production-lineage--50a7f287985c|399|
|packages/xiangsu-effect-editor--d99c4cf25ac5|1|
|packages/skills--7f67e51a1b34|73|
|packages/xiangsu-project-runtime--22d18c98f14f|78|
|packages/xiangsu-effect-workflow--fc832cf8f652|86|
|packages/xiangsu-effect-practitioner-lineage--334feb85f56b|43|
|packages/lineage-skill-main--b03fceb2a1c3|80|
|packages/xiangsu-effect-team-archive--99cafeed2906|103|
