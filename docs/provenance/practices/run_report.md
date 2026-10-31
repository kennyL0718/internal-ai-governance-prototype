# 已实施内部 AI 治理披露：探索性内容分析

## 1. Executive Summary

本研究以正式 V2 的 303 个 Positive firm-year（184 家公司）为固定样本，使用 306 个 Positive 章节中的 403 条 Binary 支持证据及有界原文上下文。DeepSeek 完成 403 条结构化主题编码；其结果属于 LLM-Based Classification。

实践主要集中在：AI治理框架、政策与程序 195/303（64.4%）、AI/ML测试、验证与风险评估 51/303（16.8%）、AI用例审查与审批把关 47/303（15.5%）。

动机主要集中在：保护数据、机密信息、知识产权与公司资产 85/303（28.1%）、降低AI法律、监管与合规风险 83/303（27.4%）、降低AI/ML性能、准确性、偏见与不良输出风险（含模型风险） 66/303（21.8%）。

上述动机频率包含明确支持的隐式标签。只采用显式证据时，前三类为：保护数据、机密信息、知识产权与公司资产 46/303（15.2%）、降低AI法律、监管与合规风险 43/303（14.2%）、确保负责任、合乎伦理与可信的AI使用 42/303（13.9%）。

目标/愿景主要集中在：保护数据、系统、机密信息、知识产权与资产免受AI相关风险 80/303（26.4%）、AI/ML模型按预期运行、准确且无不良后果 57/303（18.8%）、法律、监管与外部伦理标准合规 57/303（18.8%）。

显式披露所列风控/保护/合规/声誉目标的有 116/303（38.3%），明确连接 AI 采用、创新或价值目标的有 9/303（3.0%），两组重叠 5 个。这些是特定章节与治理证据窗口内的披露模式，不能解释为企业实际战略重要性的排序。

动机维度分布：Explicit：113（37.3%）；Implicit：76（25.1%）；Mixed：28（9.2%）；Not Disclosed：59（19.5%）；Uncertain：21（6.9%）；Observed_with_uncertainty：6（2.0%）。目标/愿景维度分布：Explicit：118（38.9%）；Implicit：55（18.2%）；Mixed：22（7.3%）；Not Disclosed：82（27.1%）；Uncertain：21（6.9%）；Observed_with_uncertainty：5（1.7%）。

自动完整性校验通过状态：True；调用最终失败 0 条，不可充分编码 34 条；待复核模型标记 77 条，涉及 58 个 firm-year。人工审核尚未开展，未报告人工准确率。

## 2. Data and Sample

年度 Positive firm-years：{'2025': 168, '2024': 93, '2023': 35, '2020': 2, '2021': 2, '2022': 3}。Item 1A Positive 章节 272 个、Item 7 34 个；3 个 firm-year 同时在两章 Positive。章节内原始证据分别 354 和 49 条。

筛选：正式 combined_firm_year_v2_panel.csv 中 implemented_internal_ai_governance_v2=1。保留每条原始 Evidence，按其 source hash、accession、Item 与 offset 关联原文；不读取 V1 主题标签。

研究范围为原有治理组合证据，以及同一 Positive 章节全部支持片段左右各 1100 字符的连续上下文块；重叠块合并。原始片段可能分别建立 AI 适用范围、风险背景和治理机制，结合阅读；引文须完整落于一个连续块，禁止跨块拼接。未对 Negative 章节或整份 10-K 做主题穷尽搜索。Not Disclosed 仅指该分析文本内未观察到，不能解释为公司没有该动机/目标。

完整 Data Inventory、路径、恢复空白标准化记录见 data_inventory.md 和 evidence_source_index.csv。

本地 V2 标准、正式 Binary 运行时冻结标准和本次只读副本 SHA-256 一致；没有用后来的规则改写原始分类。

## 3. Methodology and Codebook Development

探索样本固定为 50 个 firm-year、73 条 Evidence，seed=42；覆盖全部 11 个 GICS 行业、全部 FY2020–2022 和全部双章节 Positive，兼顾证据长短和章节。这是目的抽样，不构造概率权重。先逐 firm-year 开放编码，再综合相近主题、检查边界并冻结 Codebook。

初轮探索发现部分证据片段无法独立建立治理联系，故在固定样本内对 21 个 firm-year、38 条 Evidence 补充同章上下文开放编码。初轮 26 个模型复核标记在补充后为 16 个；这属于文本阅读范围纠正，不能作为准确率改善的估计。初轮结果、补充结果和初稿均保留独立版本。修订区分培训与持续监控，明确正式模型风险框架与具体活动的边界。

冻结类别数：{'practices': 12, 'motivations': 9, 'visions': 9}。codebook.md 记录定义、纳入/排除、相邻类别区别及代表引文。代码和 codebook.json 的哈希冻结，探索样本在全样本阶段同样重新进行闭合编码，未继承开放编码标签。

中间层级为 Evidence；最终按 CIK×FY 对每个类别取并集。跨 Evidence 或 Item 相同主题只计一次。每个标签保留精确引文及原文 offset；动机与目标另要求 relationship_quote。显式/隐式并存时，单类别统计优先 Explicit；raw_implicit_any 另存保留重叠信息。

所有百分比分母明确列入 category_statistics.csv。主分母始终为全部原始 Positive firm-years，失败、不可编码和复核记录不从分母静默移除。主表为所有通过结构/引文校验的模型标签，review_flag_sensitivity.csv 另列仅由无模型复核标记 Evidence 支撑的计数。

## 4. Governance Practices — Main Findings

|类别|Firm-year N|占全部 Positive %|不同公司数|
|---|---:|---:|---:|
|P01 AI治理框架、政策与程序|195|64.4|123|
|P04 AI/ML测试、验证与风险评估|51|16.8|27|
|P03 AI用例审查与审批把关|47|15.5|29|
|P09 持续AI监测、执行与报告|46|15.2|27|
|P08 员工AI培训与意识|35|11.6|19|
|P02 跨职能AI治理机构与委员会|29|9.6|20|
|P06 允许使用规则与第三方合同限制|26|8.6|17|
|P05 AI/ML模型风险管理机制|13|4.3|6|
|P07 技术性AI访问与数据安全控制|13|4.3|9|
|P12 AI监管监测与适应|6|2.0|5|
|P10 人工监督与专家在环审查|5|1.7|5|
|P11 AI运营暂停、安全审查与事件调查|1|0.3|1|

制度/框架存在性是最常见披露角度；具体治理活动中，测试与风险评估、审批把关、持续监督的频率相近。政策存在性与具体活动可以在同一观测中共存；这些主题具有不同披露详细度，不能用作治理成熟度评分。

这些计数描述在已披露治理样本内的主题出现频率；一个 firm-year 可具有多个标签，比例合计可以超过 100%。类别的广泛出现不能证明治理执行更有效，也不能代表所有上市公司的议题重要性。

![Governance practices](figures/01_practices_frequency.png)

## 5. Governance Motivations — Main Findings

|类别|Firm-year N|占全部 Positive %|显式 N|显式占全部 Positive %|仅隐式 N|
|---|---:|---:|---:|---:|---:|
|M02 保护数据、机密信息、知识产权与公司资产|85|28.1|46|15.2|39|
|M01 降低AI法律、监管与合规风险|83|27.4|43|14.2|40|
|M04 降低AI/ML性能、准确性、偏见与不良输出风险（含模型风险）|66|21.8|40|13.2|26|
|M06 降低员工或第三方的未授权/不合规AI使用|55|18.2|19|6.3|36|
|M08 一般人工智能风险缓释|49|16.2|33|10.9|16|
|M05 确保负责任、合乎伦理与可信的AI使用|46|15.2|42|13.9|4|
|M03 降低AI相关网络安全与技术安全风险|33|10.9|13|4.3|20|
|M07 保护声誉与重建公众信任|22|7.3|11|3.6|11|
|M09 把握人工智能机会并创造业务价值|8|2.6|8|2.6|0|

Explicit：113（37.3%）；Implicit：76（25.1%）；Mixed：28（9.2%）；Not Disclosed：59（19.5%）；Uncertain：21（6.9%）；Observed_with_uncertainty：6（2.0%）

Explicit-only 结果为上表“显式 N”，分母同为 303。隐式标签只代表文本关系可支持的模型解释；一般 AI 风险段落的邻接不能自动作为治理动机。每个动机标签的支持引文和关联引文可在 assigned_category_quotes.csv 复核。

任一动机具有显式证据的 firm-year 共 145（47.9%）；仅有隐式动机标签的共 78（25.7%）。这些计数包含已观察到的部分证据；维度状态中的 Explicit 为纯显式且完整的互斥分组，Mixed 和 Observed_with_uncertainty 另列，不能把单个状态直接当作任一显式证据总数。

显式证据口径下，信息/IP 保护、法律合规与负责任/伦理 AI 的频率接近；加入隐式关系后，法律、数据和模型风险标签的计数更高。结论应分别展示两种口径，避免把风险后果叙述全部当作直接披露的实施原因。

![Motivations](figures/02_motivations_distribution.png)

## 6. Governance Objectives / Vision — Main Findings

|类别|Firm-year N|占全部 Positive %|显式 N|显式占全部 Positive %|仅隐式 N|
|---|---:|---:|---:|---:|---:|
|V03 保护数据、系统、机密信息、知识产权与资产免受AI相关风险|80|26.4|47|15.5|33|
|V02 AI/ML模型按预期运行、准确且无不良后果|57|18.8|36|11.9|21|
|V04 法律、监管与外部伦理标准合规|57|18.8|33|10.9|24|
|V06 确保员工遵守AI治理并防止未授权AI使用|49|16.2|19|6.3|30|
|V01 负责任、伦理、可信与安全的人工智能使用|43|14.2|42|13.9|1|
|V09 一般人工智能风险预防与缓释目标|42|13.9|34|11.2|8|
|V08 重建公众信任并保护声誉|21|6.9|10|3.3|11|
|V05 实现高效、受控与创新的AI采用及价值交付|9|3.0|9|3.0|0|
|V07 确保可解释、可审计与经专家验证的AI决策流程|3|1.0|2|0.7|1|

Explicit：118（38.9%）；Implicit：55（18.2%）；Mixed：22（7.3%）；Not Disclosed：82（27.1%）；Uncertain：21（6.9%）；Observed_with_uncertainty：5（1.7%）

目标维度独立于实践。已生效政策、委员会或控制措施不会自动产生战略愿景标签；明确表达的未来治理目标可以进入目标维度，未来计划不能作为已实施实践。与 Adoption、Innovation 或价值创造的联系必须由治理相关目的/职责表述支持。

任一目标具有显式证据的 firm-year 共 144（47.5%）；仅有隐式目标标签的共 56（18.5%）。

### 风控/合规与 AI 赋能定位的描述性比较

以下为冻结编码之后的研究者描述性归组，未增设 LLM 标签。所列风控/保护/合规/声誉目标取 V02、V03、V04、V06、V08、V09 的显式证据并集；采用/创新/价值目标为显式 V05。V01 规范性 Responsible AI 与 V07 可解释/专家验证目标另外报告，不强行归入这两组。

|目标组|Firm-year N|占全部 Positive %|
|---|---:|---:|
|Listed risk, protection, compliance or reputation objectives|116|38.3|
|AI adoption, innovation or value objective|9|3.0|
|Both objective families|5|1.7|
|Neither family explicitly observed|183|60.4|

观察到 5 个 firm-year 同时明确披露所列风控/合规等目标与 AI 采用/创新/价值目标，说明在这部分披露中两类定位可以并存。
“Neither”表示未观察到上述两组的显式标签，可以包括未披露、隐式、其他目标或未解决内容，不能解释为没有战略或治理目标。

所分析文本以 Item 1A 为主，且证据最初为识别治理而收集；风险与合规的显式关联更常见，与章节功能和证据选择均有关。9 个 AI 赋能目标披露说明这类联系确实存在，较低频率不能证明其他企业不重视 AI 创新或价值。

![Vision](figures/03_visions_distribution.png)

## 7. Cross-Dimension Patterns

### 实践共同披露

- AI治理框架、政策与程序 × 员工AI培训与意识：31 个 firm-year（占全部 Positive 10.2%）；行条件比例 15.9%。
- AI治理框架、政策与程序 × 持续AI监测、执行与报告：31 个 firm-year（占全部 Positive 10.2%）；行条件比例 15.9%。
- 员工AI培训与意识 × 持续AI监测、执行与报告：25 个 firm-year（占全部 Positive 8.3%）；行条件比例 71.4%。
- AI治理框架、政策与程序 × 允许使用规则与第三方合同限制：20 个 firm-year（占全部 Positive 6.6%）；行条件比例 10.3%。
- AI治理框架、政策与程序 × AI/ML测试、验证与风险评估：17 个 firm-year（占全部 Positive 5.6%）；行条件比例 8.7%。

### 实践与显式动机

- AI治理框架、政策与程序 × 确保负责任、合乎伦理与可信的AI使用：41 个 firm-year（占全部 Positive 13.5%）；行条件比例 21.0%。
- AI治理框架、政策与程序 × 保护数据、机密信息、知识产权与公司资产：39 个 firm-year（占全部 Positive 12.9%）；行条件比例 20.0%。
- AI治理框架、政策与程序 × 降低AI法律、监管与合规风险：38 个 firm-year（占全部 Positive 12.5%）；行条件比例 19.5%。
- AI治理框架、政策与程序 × 一般人工智能风险缓释：28 个 firm-year（占全部 Positive 9.2%）；行条件比例 14.4%。
- AI/ML测试、验证与风险评估 × 降低AI/ML性能、准确性、偏见与不良输出风险（含模型风险）：20 个 firm-year（占全部 Positive 6.6%）；行条件比例 39.2%。

### 显式动机与显式目标

- 保护数据、机密信息、知识产权与公司资产 × 保护数据、系统、机密信息、知识产权与资产免受AI相关风险：45 个 firm-year（占全部 Positive 14.9%）；行条件比例 97.8%。
- 确保负责任、合乎伦理与可信的AI使用 × 负责任、伦理、可信与安全的人工智能使用：40 个 firm-year（占全部 Positive 13.2%）；行条件比例 95.2%。
- 降低AI/ML性能、准确性、偏见与不良输出风险（含模型风险） × AI/ML模型按预期运行、准确且无不良后果：35 个 firm-year（占全部 Positive 11.6%）；行条件比例 87.5%。
- 降低AI法律、监管与合规风险 × 法律、监管与外部伦理标准合规：33 个 firm-year（占全部 Positive 10.9%）；行条件比例 76.7%。
- 一般人工智能风险缓释 × 一般人工智能风险预防与缓释目标：33 个 firm-year（占全部 Positive 10.9%）；行条件比例 100.0%。

上述跨维度计数基于同一 firm-year 共同披露，不保证每种实践与每种动机之间都有逐对直接因果/目的联系。同一目的语句可能分别支持动机和目标；这些维度的共同出现部分来自共享措辞与概念联系，不能解释为独立行为机制。不作回归、因果推断或治理效果判断。

年度主题表使用每年 Positive 内部比例；FY2020、FY2021、FY2022 分别仅 2、2、3 个观测。年度间样本公司、章节和披露长度均有变化，组合效应显著限制趋势解释。重复公司跨年披露也会影响频率。

例如 FY2023–FY2025 测试/评估类的年内比例为 22.9%、16.1%、13.1%，对应绝对观测数为 8、15、22；比例下降与数量增加可以同时发生，不能据此断言企业实际评估活动减少。

![Annual themes](figures/04_practices_by_year.png)

![Co-disclosure](figures/05_practices_cooccurrence.png)

![Practice and motivation](figures/06_practices_motivations.png)

Item 图分别使用章内 Positive firm-year 分母 272 和 34；原始计数与占全部 303 的比例同时保留。不同章节的公司构成和披露功能不同，差异不能单纯归因于章节本身。

![Item topics](figures/07_item_topic_distribution.png)

## 8. Representative Disclosure Examples

每类 2–3 个不同公司真实示例（有充分材料时）见 representative_examples.md，含原始引文、公司、年份、章节、Evidence ID、offset 与解释。另列风险缓释、Responsible/Ethical AI、Adoption/Business Value/Innovation 关联，以及实践明确但动机/目标未披露的案例。证据不足不强行补足。

### 风险缓释案例：Truist Financial (TFC) FY2024 item7

Observed Disclosure：

> Truist s AI program is foundationally based on the National Institute of Standards and Technology AI Risk Management Framework Core, which provides outcomes and actions that enable dialogue, understanding, and activities to manage AI risks and develop trustworthy AI systems.

LLM-Based Classification：M08。证据 `0000092230_FY2024_item7_E01`；原文 `data/interim/documents/full_universe_item7_text/FY2024/TFC_FY2024_Item7.txt`，位置 [{'start': 110098, 'end': 110373}]。

Researcher's Interpretation：该披露把治理安排与一般风险缓释目的直接联系；引文不证明措施的实际效果。

### Responsible / Ethical AI 案例：Truist Financial (TFC) FY2024 item7

Observed Disclosure：

> Truist s AI program is foundationally based on the National Institute of Standards and Technology AI Risk Management Framework Core, which provides outcomes and actions that enable dialogue, understanding, and activities to manage AI risks and develop trustworthy AI systems.

LLM-Based Classification：V01。证据 `0000092230_FY2024_item7_E01`；原文 `data/interim/documents/full_universe_item7_text/FY2024/TFC_FY2024_Item7.txt`，位置 [{'start': 110098, 'end': 110373}]。

Researcher's Interpretation：该披露说明治理制度与可信、负责任 AI 目标的联系。

### 治理与 Adoption / Business Value / Innovation 的关联案例：Metallus Inc (MTUS) FY2024 item1a

Observed Disclosure：

> with an objective to deliver value by providing education regarding the uses, benefits and risks of AI and similar technologies in our business, establishing a governance framework and principles for our use of AI, and enabling deliberate experimentation with new technologies employing AI.

LLM-Based Classification：V05。证据 `0001598428_FY2024_item1a_E01`；原文 `data/interim/documents/full_universe_item1a_text/FY2024/MTUS_FY2024_Item1A.txt`，位置 [{'start': 38049, 'end': 38339}]。

Researcher's Interpretation：该披露将治理机制、教育和实验安排与价值目标连接。

### 实践明确、动机与目标未披露：Easterly Government Properties, Inc. (DEA) FY2025 item1a

Observed Disclosure：

> We have adopted certain generative AI tools into our systems for specific use cases reviewed by legal and information security.

LLM-Based Classification：P03。证据 `0001622194_FY2025_item1a_E01`；原文 `data/interim/documents/full_universe_item1a_text/FY2025/DEA_FY2025_Item1A.txt`，位置 [{'start': 117094, 'end': 117221}]。

Researcher's Interpretation：该 firm-year 全部分析证据均未披露动机与目标；实践可识别。未披露不代表不存在。

## 9. Limitations and Validation

- 原始 Positive firm-year 覆盖：303/303。
- Evidence 输入/成功结构化编码：403/403；未提交/最终失败 0。
- 不可编码 34；模型复核标记 77；模型提议 Emerging Theme Evidence 23（尚未确认为新类别）。
- 已分配标签 1616；最终未知类别 ID 0；最终引用验证失败 0。
- 待人工复核队列 134 条（102 个 firm-year）；包括随机 30 个 firm-year 的全部证据、隐式关系边界样本及全部模型标记。
- 输入保护：317 个输入/源文件哈希复核，修改数量 0。
- Item→firm-year 每类别并集与独立集合计数逐项对账通过；双章节重复不重复计数。

17 项离线测试通过，覆盖引文连续性、类别/关联校验、失败保留和去重聚合；另以独立脚本核验导出 CSV/JSON、原文哈希和全部已分配引文。证据见 offline_test_summary.json、independent_qa.json。

Emerging Theme 为模型提议，部分可能属于既有类别的证据不足或边界歧义，需人工确认其新颖性；本次未据此新增全样本类别。个别 Binary 支持片段在本次内容编码中仍无法解释，保留不可编码与复核状态，不改写原有 Positive，也不将其内容主题缺失强制解释为不存在。

历史结构/传输失败事件 15 次，其中精确引用校验失败 5 次、未知类别 0 次；事件清单见 request_validation_issues.csv。失败、重试和引用纠正保留于 request_manifest.jsonl 与 raw responses，最终失败表不会静默丢行。quote validation 保证文本存在，不能证明标签语义正确。原有 V2 二元判定和 Item 边界未重新人工验证。

Disclosure Content ≠ Actual Corporate Behavior。Observed Disclosure 为可追溯原文；LLM-Based Classification 为主题与显隐关系标签；Researcher's Interpretation 为对频率和共同披露的谨慎解读。本次未完成独立人工复核，不报告准确率、intercoder reliability 或将自洽性当作准确率。

## 10. LLM Configuration, Token Usage and Cost

使用现有共享 DeepSeek chat_json 客户端及凭证解析；请求 alias=deepseek-flash，temperature=0，max_tokens=16384，JSON object，timeout=120s，3 次 transport retry（2/4/8 秒），并发 16，每次执行最多 2 次结构/引用纠正请求，总恢复请求有限。缓存按精确 payload 哈希验证，断点续跑复用成功。

Codebook 单次综合步骤因默认上限截断，单独将 max_tokens 提高至 65536；历史截断响应 4 次。这些响应未进入编码数据，其 API usage 全部计入成本。初次综合请求的 JSON 格式指令也已显式补足，原始失败保留。

原流程 intended model=DeepSeek-V4.1-Flash；2026-10-18 官方页面为 DeepSeek-V4.1-Flash-1017。保留同一 API alias，并明确记录 provider 更新。实际返回模型：{"deepseek-flash":492}。

API transport attempts=502；received responses=492；分阶段请求={'open': 59, 'synthesis': 6, 'open_context_v2': 21, 'closed': 416}；未取得 token usage 的尝试=10（含 HTTP 拒绝 1、网络失败或中断请求）。

Token usage（包含收到响应的重试）：{"completion_tokens":2668658,"prompt_cache_hit_tokens":4471296,"prompt_cache_miss_tokens":517593,"prompt_tokens":4988889,"total_tokens":7657547}；其中 API 返回 reasoning_tokens=2428826，已包含在 completion_tokens 中，不重复计费求和。

运行事件 UTC 起止：2026-10-18T07:40:13.464746+00:00 — 2026-10-18T08:16:12.569066+00:00；API 工作流墙钟约 36.0 分钟。

USD 公开单价估算情景：{"off_peak":1.692247638,"peak":3.384495276}。本次周日按官方时段属于 off-peak；没有取得账户逐笔账单，因此实际扣费保留 null。未返回 usage 的失败尝试不能自行补算。

价格与模型版本来源：[DeepSeek 官方 Models & Pricing](https://api-docs.deepseek.com/quick_start/pricing/)，查询日期 2026-10-18。快照及计算依据见 pricing_snapshot.json、cost_and_token_summary.json。

复现入口：scripts/43_analyze_governance_content.py。实际阶段为 prepare → 初轮 open → 初稿 synthesize → supplement → 修订 synthesize → 研究者检查 draft → freeze → pilot → full → report。report 只读取缓存并重建派生交付，不发付费请求。完整中间状态路径见 run_manifest.json；文件哈希清单见 delivery_manifest.json。
