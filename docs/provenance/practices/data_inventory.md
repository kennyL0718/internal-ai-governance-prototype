# Data Inventory

正式来源：`outputs/full_universe_implemented_internal_ai_governance_v2/`。标准：
`docs/implemented_internal_ai_governance_v2.md`；本次未重新判断 Binary Positive。

- Positive firm-year：303；独立公司：184。
- Positive 章节：306，章节分布：{'item1a': 272, 'item7': 34}。
- 原始 Evidence：403，分布：{'item1a': 354, 'item7': 49}。
- 双章节 Positive firm-year：3；全部原文可用。
- 原文文件哈希逐一匹配；386 条原始引文精确匹配，
  17 条原流程已标记 normalized_whitespace_case 的引文在验证仅有空白/大小写差异后，
  在本次派生输入中恢复为原始 offset 对应的精确原文；同时保留 Binary 原始引文。实质不匹配为 0。
- 年度 Positive 数：{'2025': 168, '2024': 93, '2023': 35, '2020': 2, '2021': 2, '2022': 3}。
- 探索样本：50 firm-years、73 Evidence；年份分布 {2020: 2, 2021: 2, 2022: 3, 2023: 13, 2024: 14, 2025: 16}。
- 探索行业分布：{'Financials': 8, 'Health Care': 5, 'Consumer Discretionary': 5, 'Information Technology': 5, 'Industrials': 4, 'Real Estate': 4, 'Materials': 4, 'Consumer Staples': 4, 'Energy': 4, 'Utilities': 4, 'Communication Services': 3}；章节组合 {'item7': 11, 'item1a': 36, 'item1a+item7': 3}。

样本采用 seed=42、最大差异目的抽样，全部纳入 FY2020–2022 和双章节 Positive；
其余按年份、固定历史 GICS 行业、章节组合、证据总长度四分位和公司多样性补足 50。
该探索样本用于发现主题，不用于加权估计。行业来自项目保存的 sp500/sp400/sp600.csv，
未知行业保持 Unknown（全样本 0 firm-years）。

使用文件：combined_firm_year_v2_panel.csv、positive_evidence_audit.csv、
item1a_v2_classification_results.csv、item7_v2_classification_results.csv、
positive_evidence_contexts.jsonl、llm_config.json、delivery_qa.json。
本次从原始 Item TXT 按字符位置重建每条证据及左右各 1100 字符的上下文。
只编码 Positive 章节内这些治理证据及可关联上下文；未重新搜索整章新增治理段落。
因此 Not Disclosed 的范围是已选证据和有界上下文，不能外推整份 10-K。

证据路径、哈希、accession、原文和位置见 evidence_source_index.csv；
完整上下文和原始输入保护哈希位于 `data/interim/classifications/implemented_ai_governance_content_analysis/v1`。
位置沿用 Binary Workflow 的 Python read_text 换行标准化 Unicode 字符空间，
0-based [start,end)，不作字节位置或原始 HTML 页码解释；SHA-256 始终使用原始字节。

正式 Binary 标准及输出全部只读。独立研究结果写入用户指定 outputs 目录；
API 原始响应、请求、日志、缓存和待人工审核队列保存在 data/interim。
所有结果均为 LLM 主题编码，人工决定另行保存，不伪装为人工验证。

探索补充上下文：发现组合证据片段后，对初次标记的 21 个原样本 firm-year 补充开放编码；所有编码输入均保留同一 Positive 章节的全部合格 Evidence 周边连续上下文块，重叠块合并。未重新检索整章新增主题，样本和原始证据不变；引文必须完整落于单一连续块。原初开放编码、补充结果和草案均有独立版本记录，见 context_supplement_manifest.json。
