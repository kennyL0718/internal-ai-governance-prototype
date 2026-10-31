# 数据字典与统计口径

- `cik` 为保留前导零的公司字符串标识；`fiscal_year` 为财年，主键为 CIK × FY。
- `evidence_id` 唯一标识原始 V2 支持证据。部分片段分别提供 AI 适用范围、风险背景和治理机制，须结合关联上下文阅读。
- `input_file` / `input_sha256` 为来源 Item TXT 的路径和原始字节 SHA-256。`section` 保留 Item 1A / Item 7。
- `evidence_start/end` 和类别 `quote_locations` 沿用 Python `read_text` 换行标准化后的 Unicode 字符空间，0-based、左闭右开；不代表字节或 HTML 页码。
- `evidence` 为对应 offset 的精确原文；`binary_original_evidence` 保留原分类导出的引文。17 条仅有空白/大小写差异的原引用已在派生输入恢复为精确原文。
- `context_blocks` 为同一 Positive 章节各原始证据左右各 1100 字符的连续原文块，重叠合并；引文不能跨块拼接。
- `practices`、`motivations`、`visions` 保存 Evidence 级多标签 JSON，含类别、引文、解释和来源位置；后两维度另含显隐程度及治理关联引文。
- `P01`–`P12`、`M01`–`M09`、`V01`–`V09` 在 firm-year 表中为该类别是否至少出现一次。`0` 仅表示在成功编码内容中未观察到该类别，不能替代 `coding_status`、失败数或不可编码状态。
- `*_explicit` 表示该 firm-year 至少有显式关系；`*_implicit_any` 保留任一隐式关系；`*_implicit_only` 为出现该类别但没有显式关系。因此同类别 `count = explicit + implicit_only`，`implicit_any` 可能与显式重叠。
- `Not Disclosed` 限于全部已分析证据及上下文，没有外推整份 10-K 或企业实际动机。失败、不可编码和 Emerging Theme 导致的未解决状态单独保存。
- `Observed_with_uncertainty` 表示已观察到部分支持标签，同时仍有未解决内容；`Uncertain` 表示没有足够完整依据形成该维度的缺失判断。
- `review_flag` 为模型建议复核，`human_review_status=not_reviewed` 为实际状态。没有模型标记也不表示已获人工验证。
- `emerging_themes` 为模型提出的待复核新主题候选，可能包含既有类别的边界歧义；本次未据此扩展冻结类别。
- 总体类别比例的分母固定为原始 303 个 Positive firm-year；年度为该年 Positive 数；章节比较分别为 Item 1A 的 272 和 Item 7 的 34 个 Positive firm-year。所有类别按 firm-year 去重，多标签比例之和可超过 100%。
- 共同出现表衡量同一 firm-year 的共同披露，动机和目标使用显式标签。表内 row conditional percentage 的分母是行主题出现数；不声称每对主题有直接目的联系或因果关系。
- `review_flag_sensitivity.csv` 仅移除有模型标记的证据对类别计数的支持，分母仍为 303；无标记结果同样未经人工验证。
- `figure_label_dictionary.csv` 将简短图表标签映射到完整冻结类别名称，没有改变类别定义。
