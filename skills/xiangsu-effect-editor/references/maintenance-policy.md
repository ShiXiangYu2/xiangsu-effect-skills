# 人工批准的自动维护

每次使用技能，先运行 scripts/lifecycle.py check-sources --skill 技能目录，检查已记录的本地来源哈希；记录来源不可用及官方远程来源未检查，不能声称已经联网更新。

每次训练、创建、安装、升级或优化技能，必须提供 VERSION、manifest.json、来源与哈希、维护脚本和实际验证证据。没有上游来源时明确标注用户需求/本地实施，不能编造发布源。

自动流程：只读检查 → 汇总真实失败和用户纠正 → 在 artifacts 创建候选 → 做有证据的优化 → 验证 → 展示差异、版本、候选哈希、目标路径 → 等待用户同意 → 自动备份、安装、校验、回执。

prepare 命令仅生成 draft 候选和优化依据，不代表优化已经实现。智能体需要实际改进指令、脚本或引用，完成行为验证后将 manifest.status 改为 validated_candidate。版本变更应符合语义版本规则。

plan 绑定候选完整 SHA256、目标路径和当前已装版本哈希。install 的 --approval 参数为当前计划完整 SHA256，只有收到用户对展示的当前候选明确同意后才允许传入。校验参数不是人类同意的替代；不得自行制造同意、预填批准，或根据沉默、以前版本的同意来安装。候选或目标变化需要新计划和重新同意。

首次安装、覆盖、升级都需要人工同意。安装前在同卷暂存、再次验证，已有版本用 Move-Item 移到带时间戳的备份，再激活新版本。失败保存现场并恢复备份，不批量删除。所有写文件先 tmp、验证、Move-Item -Force。

命令：
```text
python scripts/lifecycle.py audit --skill SKILL_DIR
python scripts/lifecycle.py check-sources --skill SKILL_DIR
python scripts/lifecycle.py prepare --skill SKILL_DIR --feedback FEEDBACK.txt --out NEW_CANDIDATE_DIR
python scripts/lifecycle.py plan --skill CANDIDATE_DIR --target-root CODEx_SKILLS_ROOT WORKBUDDY_SKILLS_ROOT --out PLAN.json
python scripts/lifecycle.py install --plan PLAN.json --approval APPROVED_PLAN_SHA256
```

自动检查在技能调用和维护任务中执行。本包不自行注册常驻服务、定时任务或后台下载；需要定时巡检时按照用户明确的时间安排配置。旧技能需要逐个补齐上述资料，不能说所有已安装技能已经改造，也不能在一个技能里静默覆盖其他技能。
