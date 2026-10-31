# Firm Size × Industry 与 AI Governance 阳性率，FY2023–FY2025

## 主要发现

1. 全样本阳性率从 **2.43%（35/1,441）升至 11.50%（168/1,461）**，累计增加 **9.07 个百分点**。Positive 增加 133，分母增加 20，两类变化均已单独保留。
2. 总体规模梯度稳定存在，2025 年 Large / Mid / Small 为 **13.81% / 10.97% / 9.93%**。行业内部的梯度存在明显异质性：pooled Large 高于 Small 的行业有 6/11 个，严格 Large > Mid > Small 只有 3/11 个。Large–Small 总体差距在 2024 年扩大，2025 年随 Small 加速增长而收窄。
3. **信息技术业在三组均较高，金融业优势集中于 Large 和 Mid。** Pooled 信息技术业 Large / Mid / Small 分别为 13.68% (29/212)、13.19% (19/144)、7.11% (14/197)，行业内排名依次为第 2、1、3。金融业 Large 为 24.30% (52/214)，Small 为 4.05% (14/346)，后者低于 Small 总体 4.87%。Small Health Care 的率最高（9.36% (19/203)）。
4. 33 个组合中，28 个上升、2 个下降、3 个持平。增长广泛分布，但部分高变化率来自很少的 Positive，例如 Mid 通信服务业从 0/6 变为 1/6，增加 16.67 个百分点。Large 金融业的 11/70 → 22/72 提供了更充分的描述性支持。
5. 三年共同有效的 **1,413 家公司**仍呈现明显增长，覆盖变化未消除总体趋势。Pooled 每家公司最多贡献三个 firm-years，重复观察会提高数量，不能解释为同等数量的独立公司证据。

## Corporate Hierarchy × AI Governance 的研究启示

规模与行业可能共同影响所观察到的 Governance–Hierarchy 关系。大型企业可能同时具有更多组织层级、更多披露资源和更正式的合规流程；金融业及信息技术业可能因监管、数据处理或 AI 业务需求更早披露治理措施。这些是待检验的机制解释，本分析未观察组织层级、治理质量或真实实施时间。

同一行业内的规模梯度并不普遍，说明仅比较全样本平均值可能混合了规模、行业构成与两者交互差异。金融业的大型公司集中出现 Governance Positive，可能使“层级多的公司治理更多”的原始相关性增强；Health Care 等行业中 Small 的阳性率更高，又可能掩盖或反向影响这一关系。因此，当前结果支持将 **Year × Size × Sector 单元作为后续比较的基础**，并先核对每个单元的层级分布、有效样本量和 Positive 数量。

后续研究可在同一 FY、同一 Sector 和同一规模组内比较不同 hierarchy 的公司，并检查规模与行业组合是否具有足够重叠。汇总比较时，可报告共同权重下的描述性率、行业内结果和共同有效样本结果。固定指数标签只能粗略表示规模，未来若取得逐年市值、雇员数和历史行业归属，应进一步核对。当前数据没有 hierarchy 指标，尚无法计算这些结构因素对 Governance–Hierarchy 相关性的实际解释份额。对极稀疏单元应保留分子分母，避免从少数公司推导稳定机制。

## 样本、测量与分母

| 年份 | Positive Rate（Positive N / Total N） | 有效覆盖率 | 排除 firm-years |
|---|---|---|---|
| 2023 | 2.43% (35/1441) | 96.07% | 59 |
| 2024 | 6.38% (93/1458) | 97.20% | 42 |
| 2025 | 11.50% (168/1461) | 97.40% | 39 |

每年固定样本框为 1,500 家公司，三年共 4,500 个潜在 firm-years。实际纳入 4,360 个，Positive 296 个，pooled 总体率 6.79%。2023/2024/2025 排除 59/42/39 个，分别包含 1 个缺失 CIK（Moog）及 58/41/38 个双章节均不可用观察。缺失 CIK 只按原框 ticker/FY 审计，未按空 CIK 合并。缺失分类全部排除，未填为 Negative。

**Positive Rate = 本单元 Positive firm-years / 本单元有效二元分类 firm-years × 100%。** 采用 `implemented-internal-ai-governance-v2.0` 已合并的 0/1 标签，每个 CIK/FY 计一次。任一有效章节 Positive 得到 Positive。沿用原始 observed-section 口径：仅一个章节可用且该章节 Negative 时，firm-year 可为 Negative；另一个章节缺失的状态继续保留。双章节均不可用的观察不进入分母。

规模为 S&P 500 → Large、S&P MidCap 400 → Mid、S&P SmallCap 600 → Small。规模和 GICS 11 Sector 均来自 **2026-09-19 固定指数成份快照**，统一应用于全部年份，未代表 2023–2025 逐年历史归属。分析覆盖当前固定成份框，具有回溯归类和存续选择限制。

检查结果：三年非空 CIK/FY 唯一数为 4,497，重复 CIK/FY 为 0；规模和行业映射覆盖 1,500/1,500 家，冲突为 0。旧规模面板的 Governance 字段与当前 v2 权威结果逐行一致，输入哈希与封存交付记录一致。

这些是 **年报可观察章节中披露的已实施内部 AI Governance 的自动分类结果**。Negative 表示该口径下未识别到符合标准的 Positive。人工语义验证尚未完成，不能将零阳性披露或 Negative 扩展为公司实际不存在治理。

## 规模差异及其变化

| 规模 | 2023 | 2024 | 2025 | 2023→2025（pp） | Pooled |
|---|---|---|---|---|---|
| Large | 4.39% (21/478) | 9.69% (47/485) | 13.81% (67/485) | +9.42 | 9.32% (135/1448) |
| Mid | 2.33% (9/387) | 6.20% (24/387) | 10.97% (43/392) | +8.64 | 6.52% (76/1166) |
| Small | 0.87% (5/576) | 3.75% (22/586) | 9.93% (58/584) | +9.06 | 4.87% (85/1746) |

Large–Small 总体差距依次为 **3.53、5.94、3.88 pp**，先扩大后收窄；2025 相比 2023 仍增加 0.36 pp。2024→2025 年 Large 增长 4.12 pp，Small 增长 6.18 pp。Large–Mid 的端点差距从 2.07 pp 增至 2.85 pp，Mid–Small 从 1.46 pp 缩至 1.04 pp。

2023/2024/2025 年 Large 高于 Small 的行业分别为 7/7/5 个。2025 年 Health Care（Small 12/68，17.65%；Large 8/58，13.79%）与 Materials（Small 4/25，16.00%；Large 0/24）呈相反规模排序。消费可选行业 Mid 高于其他两组。规模优势需要行业内检查。

## 行业与规模的组合差异

下表为三年 pooled 率，每个值同时给出 Positive N / Total N。Pooled 用分子、分母求和计算，未对年度率作简单平均。

| Sector | Large | Mid | Small | 全规模 |
|---|---|---|---|---|
| Information Technology | 13.68% (29/212) | 13.19% (19/144) | 7.11% (14/197) | 11.21% (62/553) |
| Financials | 24.30% (52/214) | 8.60% (16/186) | 4.05% (14/346) | 10.99% (82/746) |
| Health Care | 7.43% (13/175) | 1.92% (2/104) | 9.36% (19/203) | 7.05% (34/482) |
| Real Estate | 8.99% (8/89) | 4.65% (4/86) | 5.26% (7/133) | 6.17% (19/308) |
| Utilities | 5.49% (5/91) | 7.14% (3/42) | 5.56% (2/36) | 5.92% (10/169) |
| Materials | 2.78% (2/72) | 5.33% (4/75) | 7.89% (6/76) | 5.38% (12/223) |
| Industrials | 5.04% (12/238) | 5.14% (13/253) | 4.10% (11/268) | 4.74% (36/759) |
| Consumer Staples | 9.00% (9/100) | 2.27% (1/44) | 0.00% (0/78) | 4.50% (10/222) |
| Energy | 1.75% (1/57) | 6.12% (3/49) | 4.26% (4/94) | 4.00% (8/200) |
| Consumer Discretionary | 2.86% (4/140) | 6.06% (10/165) | 2.31% (6/260) | 3.54% (20/565) |
| Communication Services | 0.00% (0/60) | 5.56% (1/18) | 3.64% (2/55) | 2.26% (3/133) |

信息技术业三组均高于各自规模组的总体 pooled 率。金融业在 Large、Mid 分别居第一、第二，Small 低于本规模组总体率，行业优势随规模明显变化。Small 组 Health Care 最高、Materials 次之，后者 pooled 为 6/76，Positive 仍然较少。该比较使用行业与规模交叉单元内部的率，保留了组内更细的规模、业务或 AI 使用差异。Large Consumer Staples 为 9/100，Small 为 0/78，也呈现明显的描述性反差。Large Financials 是 pooled 率最高的单元。

Mid Communication Services pooled 为 1/18（5.56%），仍属于小样本；2025 单年较高率仅对应一家。Small Utilities pooled 仅 2/36，2025 的 16.67% 来自 2/12，不能视为稳定行业优势。图中 `*` 与斜线标记 Total N<20，`†` 标记 Positive N<5（含零）；这是透明的描述性提醒阈值，未进行统计显著性检验。NA 对应无有效观察，率和变化留空。本次主样本 99 个年度单元及 33 个 pooled 单元均有有效观察，其中 21 个年度单元、1 个 pooled 单元 N<20。

## 2023–2025 的增长来自哪里

| Sector | 规模 | 2023 | 2025 | 率变化（pp） | Positive N 变化 | 解释提醒 |
|---|---|---|---|---|---|---|
| Communication Services | Mid | 0.00% (0/6) | 16.67% (1/6) | +16.67 | +1 | N<20 |
| Utilities | Small | 0.00% (0/12) | 16.67% (2/12) | +16.67 | +2 | N<20 |
| Health Care | Small | 1.52% (1/66) | 17.65% (12/68) | +16.13 | +11 | 2023 Positive<5 |
| Materials | Small | 0.00% (0/25) | 16.00% (4/25) | +16.00 | +4 | 2023 Positive<5 |
| Real Estate | Small | 0.00% (0/43) | 15.56% (7/45) | +15.56 | +7 | 2023 Positive<5 |
| Financials | Large | 15.71% (11/70) | 30.56% (22/72) | +14.84 | +11 |  |
| Information Technology | Mid | 4.17% (2/48) | 18.75% (9/48) | +14.58 | +7 | 2023 Positive<5 |
| Information Technology | Large | 5.63% (4/71) | 20.00% (14/70) | +14.37 | +10 | 2023 Positive<5 |

全部 11 个行业的汇总率在 2023→2025 年均上升。Health Care 增长 12.40 pp（2/158 → 22/161），Financials 增长 11.96 pp（12/248 → 42/250），Information Technology 增长 11.96 pp（8/184 → 30/184）。按 Positive 数量，Financials、Industrials、Information Technology、Health Care 分别净增 30、24、22、20 个，合计贡献 96/133 个净增 Positive。该数量贡献与组内阳性率分别解释，完整统计保留在边际表中。

Utilities、Communication Services 的部分规模单元分母很小，少数新增 Positive 就会产生较大的百分点变化。率变化需要同时检查分子分母，完整 CSV 已分列各期 Positive N、Total N 及变化。

只有 Large Consumer Discretionary 与 Mid Materials 的 2023→2025 率下降，两组都减少 1 个 Positive，分母基本稳定。Large Materials 在端点均为 0/24，但 2024 年为 2/24，端点变化 0 不代表三年没有波动。Financials Large–Small 差距扩大；Health Care、Real Estate 的 Small 增长更快，规模差距缩小或反向。行业和规模差异的演变呈局部扩大与局部收敛并存。

同一规模内，11 个行业阳性率的最大值与最小值之差在 2023→2025 年分别为：Large 15.71→30.56 pp；Mid 8.00→14.75 pp；Small 3.08→17.65 pp。三组行业极差均扩大，但极值容易受到稀疏 Positive 的影响，仅作描述。

## 覆盖变化检查

| 描述性检查口径 | 2023 | 2024 | 2025 | 2023→2025（pp） |
|---|---|---|---|---|
| 三年共同有效公司 | 2.48% (35/1413) | 6.44% (91/1413) | 11.54% (163/1413) | +9.06 |
| 两章节均有效 | 2.52% (33/1310) | 6.65% (89/1338) | 11.77% (157/1334) | +9.25 |

共同有效样本固定公司和分母，支持总体增长并非单纯来自有效样本数量增加。两章节均有效结果提供章节覆盖检查，样本集合仍可能逐年变化；它没有补齐缺失章节，也不替代主口径。对应的 99 个年度单元和规模、行业边际统计均保存在 `coverage_sensitivity.csv`。这些检查只用于描述稳定性。

## 图表与可复现文件

![Figure 1](<C:/Users/62638/DESKTOP/不拥抱AI/ai-restrictions-concerns/outputs/figures/governance_size_industry_v1_20261028/figure1_annual_positive_rate.png>)

![Figure 2](<C:/Users/62638/DESKTOP/不拥抱AI/ai-restrictions-concerns/outputs/figures/governance_size_industry_v1_20261028/figure2_rate_change_2023_2025.png>)

![Figure 3](<C:/Users/62638/DESKTOP/不拥抱AI/ai-restrictions-concerns/outputs/figures/governance_size_industry_v1_20261028/figure3_pooled_positive_rate.png>)

- `outputs/tables/governance_size_industry_v1_20261028/year_size_sector_statistics.csv`：99 行主统计，包含分子、有效分母、覆盖、两章节覆盖、稀疏标记和三段率变化。
- 同目录 `rate_changes.csv`：33 行组合的端点分子分母、Positive N / Total N 变化和百分点变化；`pooled_statistics.csv`：33 行 pooled 统计及不同公司数；`marginal_statistics.csv`：总体、规模和行业边际统计；`size_gaps.csv`：同行业内规模差；`coverage_sensitivity.csv`：共同有效样本与两章节覆盖检查。
- `data/interim/panels/governance_size_industry_v1_20261028/observation_audit.csv`：4,500 行纳入/排除审计，可重建的 interim 审计数据。
- `outputs/reports/governance_size_industry_v1_20261028/`：本报告、QA、输入输出 SHA256 清单和代码快照。

主表 `total_n` 为有效分类分母，`frame_n` 为潜在样本框数量；`positive_rate_pct` 的单位为百分比，`rate_change_*_pp` 为百分点。三段变化均按同一 Size × Sector 计算，在该组合的三年行中重复，便于单表读取。小样本阈值和稀疏 Positive 标记可在 QA 中核查。

输入为 `outputs/full_universe_implemented_internal_ai_governance_v2/combined_firm_year_v2_panel.csv` 与 `exclusion_manifest.csv`；复用 `data/interim/panels/firm_size_ai_disclosure_v1_20261026/firm_year_size_panel.csv`，并用 `data/interim/documents/full_universe_item1a_manifest.csv` 和 `data/raw/universe/sp500.csv`、`sp400.csv`、`sp600.csv` 核对映射。Governance v2 的 `delivery_qa.json` 与 `delivery_manifest.json` 为版本和封存依据。仅使用现有 Governance 标签确定纳入与否。

运行：`.venv/Scripts/python.exe scripts/71_analyze_size_industry_governance.py`；独立核对：`.venv/Scripts/python.exe scripts/72_verify_size_industry_governance.py`。图表均为 300 DPI PNG。未下载数据、未发起 LLM 调用、未覆盖原始分类或提升至 processed 数据。
