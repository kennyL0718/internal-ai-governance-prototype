# AI Governance Practices Annual Composition

来源分类 Run：`implemented-ai-governance-content-v1-20261018`。

## 数据与分母

- 最终交付 firm-year 分类：`outputs/implemented_ai_governance_content_analysis/firm_year_content_panel.csv`。
- 主统计：同目录 `category_statistics.csv`；冻结类别：`codebook.json` / `codebook.md`，P01–P12 全部保留。
- Evidence：同目录 `evidence_level_coding.csv`、`assigned_category_quotes.csv`；QA：`qa.json`、`independent_qa.json`；输入哈希见 `visualization_manifest.json`。
- 分子 n(k,t)：财年 t 有既有有效 Evidence 支持的 Practice k 的不同 firm-year 数。以 CIK×Fiscal Year×Practice 去重，跨 Item 1A / Item 7、多个引文均只计一次。
- 年度分母 A(t)=Σk n(k,t)；组成 Share(k,t)=n(k,t)/A(t)。图2色块为 n(k,t)，堆叠柱高为 A(t)。
- 样本为原 Governance v2 Positive firm-years。未观察到 Practice 的 firm-years 不贡献 assignment；保留其状态，不追加缺失类或负类。

## QA 范围与结果

Practice 数据没有 Purpose 的 `qa_passed` / `semantic_verdict` 字段，也没有 Practice 级 Explicit/Implicit 标记。此次采用既有技术 QA：成功编码、非 uncodable、有非空原文引文和位置、原 TXT SHA-256 匹配、引文逐字与位置匹配且位于提供的上下文内、Evidence—panel—主统计一致。显性 Evidence 在这里指现有标签具有可定位的原文支持；此次未新增语义判定。

现有 QA 标记完整性通过；重新检查 606 个 Practice Evidence 标签、284 个支持 TXT 和 84 个全期/年度主统计单元格，全部一致。所有 467 个去重 assignments 均有有效支持；年度相加=全期主统计相加。所有年度组成之和=100%。

样本 303 个 firm-years，184 家公司；281 个至少有一个 Practice，107 个有多个。未观察到 Practice 的 22 个 firm-years 不增加分母 A。

保留既有主统计中的有引文标签，包括仅由模型 review_flag Evidence 支持的 23 个 assignments。review_flag 是待复核标记，现有主统计未将其移除；单独剔除会改变本次要求复用的样本口径。原交付待人工复核队列 134 条，人工完成数 0。技术 QA 与独立人工语义验证分别记录；图中结果仍为自动披露分类。

|Fiscal year|Governance-Positive firm-years|至少一项 Practice 的 firm-years|Assignments A|
|---|---:|---:|---:|
|FY2020|2|2|5|
|FY2021|2|2|5|
|FY2022|3|3|6|
|FY2023|35|32|54|
|FY2024|93|86|135|
|FY2025|168|156|262|

## FY2023–FY2025 组成

年度 assignments 从54增至135、262。P01 框架、政策与程序的组成占比从31.5%升至44.4%、44.7%，增加主要出现在FY2023→FY2024。P04 测试、验证与风险评估从14.8%降至8.4%，对应计数从8增至22；P03 用例审查与审批从13.0%降至8.8%，计数从7增至23。两者的相对权重下降伴随绝对计数增长。P02 跨职能治理机构与委员会在FY2025占7.3%，高于FY2023的5.6%。

|Practice ID 与冻结名称|FY2023 n / share|FY2024 n / share|FY2025 n / share|2023→2025 pp|
|---|---:|---:|---:|---:|
|P01 AI governance frameworks, policies, and procedures|17 / 31.5%|60 / 44.4%|117 / 44.7%|+13.2|
|P04 AI/ML testing, validation, and risk assessment|8 / 14.8%|15 / 11.1%|22 / 8.4%|-6.4|
|P03 AI use-case review and approval gatekeeping|7 / 13.0%|14 / 10.4%|23 / 8.8%|-4.2|
|P09 Ongoing AI monitoring, enforcement, and reporting|7 / 13.0%|12 / 8.9%|24 / 9.2%|-3.8|
|P08 Workforce AI training and awareness|5 / 9.3%|12 / 8.9%|18 / 6.9%|-2.4|
|P02 Cross-functional AI governance bodies and committees|3 / 5.6%|7 / 5.2%|19 / 7.3%|+1.7|
|P06 Permissible-use rules and third-party contractual restrictions|3 / 5.6%|7 / 5.2%|16 / 6.1%|+0.6|
|P05 Model risk management regime for AI/ML models|2 / 3.7%|3 / 2.2%|5 / 1.9%|-1.8|
|P07 Technical AI access and data-security controls|1 / 1.9%|3 / 2.2%|9 / 3.4%|+1.6|
|P12 AI regulatory monitoring and adaptation|0 / 0.0%|2 / 1.5%|4 / 1.5%|+1.5|
|P10 Human oversight and expert-in-the-loop review|0 / 0.0%|0 / 0.0%|5 / 1.9%|+1.9|
|P11 AI operational pause, safety review, and incident investigation|1 / 1.9%|0 / 0.0%|0 / 0.0%|-1.9|

FY2023–FY2025 的构成变化与绝对 assignment 增长应分别阅读。所有比例描述所分析 10-K 披露中的 Practice 标签组成；不直接表示企业治理实践采用率、治理效果或因果关系。FY2020–FY2022 每年仅2–3个 Positive firm-years，5–6个 assignments，灰底标记其组成不稳定。

## 版式与复现

直接复用 `src/ai_restrictions/governance_purpose_inductive_visualization.py` 的 PALETTE、configure、title、footer、grid、legend_axis、save。16×10.8英寸、DejaVu Sans、300 dpi、左右轴区/图例布局、灰底和标注阈值保持 Purpose Annual Composition 风格。颜色按冻结 P ID 顺序固定，堆叠及图例按全期计数降序；12类均保留且使用不同颜色。大色块阈值为6.7%；计数图为最大年度 A 的6%。附 PNG 与 PDF。

项目根目录执行：`.venv/Scripts/python.exe scripts/63_plot_governance_practices.py`。

也可运行本目录 `plot_governance_practices.py`，使用同目录保存的 `purpose_plot_style.py`；支持 `--output-dir`。依赖 matplotlib、numpy。源模块位于 `src/ai_restrictions/governance_practices_visualization.py`。此流程不含 LLM 请求或既有分类写入。

`annual_practice_composition.csv` 保存72个年度×类别绘图值；`annual_assignment_totals.csv` 保存年度样本数和 A；`practice_color_map.csv` 保存固定配色；`visualization_qa.json` 保存数值及画布检查；manifest记录输入、代码、输出哈希与依赖版本。

## 导出与复现实测

独立核对72个年度类别绘图单元格与主统计全部一致；从交付目录单独执行脚本，在相同环境下2个PNG、2个PDF及全部3个CSV的SHA-256完全一致。PNG为4800×3240、300 dpi；PDF为单页矢量并嵌入字体。两张PNG已检查图例、色块标注、柱顶总数与图注的布局，输入前后哈希保持一致。
