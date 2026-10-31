# Implemented Internal AI Governance — Binary Classification Guideline (v2)

> **研究用途：** 美国上市公司 Form 10-K（主要为 Item 1A — Risk Factors 与 Item 7 — MD&A）中，公司层面的 *implemented internal AI governance* 披露识别。  
> **判定单位：** firm-year；原始文本按 section 独立保留证据，随后按规则整合。  
> **核心变量：** `implemented_internal_ai_governance_v2` ∈ {1, 0}；材料不足时使用独立的 missing / review 状态，不强行编码为 0。  
> **理论参照：** NIST (2023), *AI Risk Management Framework (AI RMF 1.0)*，尤其是 Section 5.1 的 **GOVERN** 功能及 GOVERN 1–6。  
> **版本原则：** 只识别 **Binary Positive / Negative**；不再设置 G1/G2/G3 等治理内部子类。AI Restrictions 作为单独研究变量保留。

## 1. 研究概念与测量边界

### 1.1 核心定义

**Implemented Internal AI Governance（已实施的企业内部 AI 治理）**：企业已经建立或实际执行的组织性安排，通过政策、职责分工、监督、审查、风险控制或其他管理实践，对自身 AI 系统或 AI 相关活动的负责任开发、采购、部署、运行、提供或使用进行指导、监督、评估或控制。

**可观测指标的定义**：在被检查的 10-K 披露中，是否存在足够明确、可追溯的文本证据，证明企业至少存在 **一项符合标准且已经实施的内部 AI 治理安排或实践**。

该变量衡量的是 **disclosed evidence of implemented governance（已披露的实施证据）**，**不是**企业真实治理状况的完整观测，更不是治理质量、有效性、成熟度、覆盖率或对 NIST AI RMF 的合规程度。

### 1.2 NIST 的作用与本研究的选择

NIST AI RMF 的 GOVERN 功能覆盖组织政策与程序、问责和职责、人员培训、监督、风险沟通、反馈机制以及第三方 AI 风险管理，并贯穿 MAP、MEASURE、MANAGE。其类别并非完整清单、强制清单或现成的披露编码规则。

因此，本研究**借鉴 NIST 界定哪些实践具有 AI governance 的实质内容**，再自行建立审慎的、适用于 10-K 披露的二元测量边界。下述五条件交集、证据要求、仅限披露文本、以及“孤立 restrictions 不足以构成 positive”等均为**研究者制定的操作规则**，不能表述为 NIST 的官方判定标准。

## 2. 核心分类规则：五条件同时满足

只有当**至少一项可识别的治理安排或实践同时满足 C1–C5** 时，才将有效观测编码为 `1 (Positive)`。这些条件可以由相邻句子或可明确关联的上下文共同支持，但不得拼接互不相关的表述来补足缺失要件。

### C1. 企业内部归属（Internal organizational scope）

治理安排必须由**披露公司自身**（含董事会、管理层、员工、内部职能团队或获授权的业务部门）建立、承担或实施，并且针对公司自身开发、采购、部署、运行、提供或使用的 AI 系统及相关活动。

- **可纳入：** 公司对员工使用第三方生成式 AI 工具实行的内部审查；公司对向客户提供的 AI 产品所实施的内部风险控制；针对一个特定 AI 应用的内部法律/安全评审。
- **不可纳入：** 仅介绍供应商、客户或监管机构的 AI 政策，而未披露本公司实施了相应治理；单纯说明外部法律规定。
- **范围限制：** 某个具体业务或项目合格即可，但不得据此推断已经覆盖全公司。

*NIST 对应：GOVERN 2.1–2.3、6.1–6.2。*

### C2. 明确适用于 AI（Explicit AI application）

文本必须能够**明确地**将该安排与 AI、machine learning、generative AI 或可识别的 AI 工具、系统或活动联系起来。

- 既有的 enterprise risk management、legal、information security、privacy 或 compliance 架构可以算作 AI governance，**前提是披露明确说明它们已适用于公司的 AI 活动**。
- 不要求文件名包含 “AI Policy”，也不要求专门成立 AI 委员会。
- 泛化的 cybersecurity、privacy、board oversight 或合规表述，若未指向 AI，不满足本条件。

*NIST 对应：GOVERN 1.1–1.4（尤其 1.2）、3.2。*

### C3. 已建立或已执行（Established / implemented / in force）

文本必须表明治理政策、职责、制度、流程、控制措施或具体治理实践**已经存在、正在生效，或已在相关期间执行**。

- **可能支持 Positive：** `we maintain`、`we have implemented`、`is in place`、`is responsible for`、`undergoes review`；以及由明确的内部法律、合规或信息安全部门 `was reviewed by` 的实际审查。
- 已确立的定期审查机制若明确指派当前责任与程序，即使下一次审查尚未发生，也可以合格。
- **不合格：** `we plan to establish`、`we intend to develop`、尚未批准的建议、仅表达应当加强治理的愿望。
- 仅披露已经终止的历史制度，不能据此认定当前 firm-year 存在治理。

*NIST 对应：GOVERN 1、2、4、6；GOVERN 1.5 允许已建立职责支撑的后续监测计划。*

### C4. 可识别的治理机制（Identifiable governance mechanism）

必须识别到**至少一项具有组织管理属性的具体机制或实践**，其作用是指导、监督、评估或控制 AI 相关的风险、责任、安全、合规或负责任使用。

可接受的证据包括但不限于：

| 可能的治理实践（仅用于识别边界，不是分类子类） | NIST 参考 |
|---|---|
| 已生效的内部 AI 使用政策、responsible-AI 政策，或已将 AI 纳入既有风控/合规程序 | GOVERN 1.2–1.4 |
| 董事会、管理层、风险/法律/安全部门已承担明确的 AI 风险监督职责 | GOVERN 2.1、2.3 |
| 针对 AI 的法律、隐私、网络安全、安全性、偏见或模型风险的审查、批准、监测及控制 | GOVERN 1.3–1.5、3.2、4.3 |
| 已实施的 AI 风险管理或安全使用培训（而非普通使用技巧培训） | GOVERN 2.2、4.1 |
| 人类监督、AI 系统清单、事件处置、风险反馈升级与安全退役的治理程序 | GOVERN 1.6–1.7、3.2、4.3、5.1–5.2 |
| 企业执行的第三方 AI 工具/供应商尽调、风险审批与应急管理 | GOVERN 6.1–6.2 |

**重要的充分性边界：**

1. 识别到一次明确的、针对某项 AI 应用进行的**内部法律或信息安全风险审查**，可以证明该特定范围内存在已实施治理实践；**不要求**同时披露适用于全公司的正式审批政策。
2. 技术测试只有在文本揭示**安全、合规、偏见、隐私、责任或风险监督用途**时才可能合格。普通准确率、产品性能或商业效果测试本身不够。
3. 仅称部署 AI、发展 AI 战略、重视 AI 风险、坚持伦理原则或开展技术创新，并不等于治理机制。
4. 不要求机制具有独立品牌、单独政策文档、持续性记录或已被证明有效；但必须能够看出实际组织性的治理内容。

### C5. 可追溯证据与审慎归因（Evidence-based attribution）

每一条 Positive 均需能够引用**原文证据**，支持以下连接：

**披露公司 → 明确的 AI 活动/系统 → 已建立或执行的安排 → 治理用途。**

可以使用紧邻上下文确定主语、代词、时态、日期和适用范围；**不得臆造**文本未披露的委员会、公司政策、审批义务、全公司覆盖、治理成熟度或已实现效果。

> **判定核心：** NIST 为治理内容提供概念参照；“必须抽取到这条完整证据链”是本研究为提高可复核性设定的额外要求。

## 3. 优先排除规则（Priority exclusions）

以下情况在**不存在另一条满足 C1–C5 的证据**时，应判为 `0 (Negative)`：

1. **AI risk awareness ≠ governance**：仅描述 AI 风险、潜在诉讼、外部监管压力、一般忧虑或伦理愿景。
2. **AI adoption ≠ governance**：仅披露 AI 使用、产品发布、投资、研发或模型训练。
3. **Commercial/technical quality ≠ governance**：仅有准确率、效率、功能或竞争力测试，未明确风险/安全/监督内容。
4. **Future plan ≠ implementation**：尚未建立的 AI 风险管理框架、未来计划成立的委员会或拟议政策。
5. **Generic policy ≠ AI governance**：一般风险管理、隐私、信息安全制度未明确适用于 AI。
6. **External governance ≠ internal governance**：仅描述法规、行业标准或第三方政策，没有本公司已实施安排。
7. **Board attention ≠ risk oversight**：董事会仅讨论 AI 商机或趋势，但无清晰 AI 风险监督责任或治理安排。
8. **Bare restriction ≠ implemented governance（本研究的严格边界）**：仅说“我们禁止员工把保密数据输入 AI 工具”，而未识别到公司 AI 治理政策、现行制度框架、执行/监督程序或其他治理实践，**在本指标中仍编码为 0**。若披露明确指向一项**已存在的内部 AI 使用政策或制度**，则可以满足 C4。

**关于第 8 条：** NIST 的 GOVERN 并未否认使用限制属于治理工具；将“孤立的限制条款”排除，是为了使本研究的 *Implemented Internal AI Governance* 与单独的 *AI Use Restrictions* 变量保持概念区分。**该规则是研究者定义，并非 NIST 的规定。** 不应将所有 restrictions 一概排除：同一段文本若有充分的治理制度证据，仍可判 Positive。

## 4. 判定示例（全部为假设披露，不代表真实公司）

| 10-K English disclosure（示例） | 结果 | 判定依据 |
|---|---|---|
| “We maintain an internal policy governing employees' use of generative AI tools.” | **1** | 明确存在并适用于公司 AI 使用的内部政策 |
| “Our existing enterprise risk committee is responsible for oversight of AI deployment risks.” | **1** | 既有组织承担明确 AI 风险监督责任 |
| “Our legal and information-security teams reviewed proposed AI use cases for privacy and security risks.” | **1** | 已执行的具体 AI 风险审查；不推断全公司统一审批 |
| “Third-party AI tools undergo a privacy and risk review before employees may use them.” | **1** | 公司内部对第三方 AI 工具的风险审核 |
| “Employees complete required responsible-AI risk and safety training.” | **1** | 已开展风险与安全管理培训 |
| “Employees must comply with our existing internal AI use policy.” | **1** | 明确的现行内部 AI 制度 |
| “We evaluate model accuracy before releasing AI features.” | **0** | 只有性能测试，缺少风险或监督机制 |
| “We face material cybersecurity and AI risks.” | **0** | 只有风险识别 |
| “We intend to establish an AI governance framework.” | **0** | 尚未实施 |
| “We prohibit employees from entering confidential data into AI tools.” | **0（严格规则）** | 孤立的禁止行为陈述，没有额外制度/治理证据 |
| “Our board regularly discusses emerging AI opportunities.” | **0** | 仅讨论业务机会，并非明确的治理监督 |
| “Our cybersecurity policies apply across all information systems.” | **0** | 未明确建立与 AI 的联系 |
| “Our risk management function reviews AI-related privacy incidents and escalates findings to management.” | **1** | 已运行的风险审查与升级流程 |

**敏感性边界：** 示例中 “reviewed proposed AI use cases” 是已实施的一次监督行为，可以为 Positive；“we will review AI use cases” 若没有已建立的程序、责任或执行证据则不够。不要把两者混同。

## 5. 实际判定流程

按下列顺序评估每条候选证据；发现一条满足全部条件的证据，即可在充分观测的范围内判 Positive。

1. **定位主体：** 是否为本公司实际承担或执行的内部治理？（C1）
2. **核验 AI 联系：** 制度/流程是否明确适用于 AI 活动或系统？（C2）
3. **核验已实施状态：** 是否已经建立、正生效、或确实实施过？是否与所研究财年具有时间关联？（C3）
4. **识别实质机制：** 是否有风险、责任、安全、合规或负责任使用的组织性治理内容？是否仅为 risk talk、AI adoption、纯技术测试或孤立 restrictions？（C4 与优先排除规则）
5. **核查证据链：** 是否能够用原文及紧邻上下文支持前四点，而无额外推断？（C5）

**判定：**

- **Positive（1）：** 在已检查材料中至少找到一项同时满足 C1–C5 的证据。
- **Negative（0）：** 材料已充分检查，但未找到任何符合标准的证据。仅表示 **not evidenced in the observed disclosure**；**不等于**公司现实中不存在 AI governance。
- **Review / Missing（不赋 0）：** 关键段落含义模糊，无法判断是否已实施、由谁执行或有何治理用途；或必要原始材料缺失、提取失败、章节不完整。将这种情况记录为独立状态，按可复核证据处理。

### 5.1 时间口径：fiscal year 与 filing date

- 记录并区分 `fiscal_year_end` 与 `filing_date`；它们可能跨年度。
- 如果文本**明确**指出治理措施直到该 fiscal-year end **之后**才首次实施，不应自动视为该已结束财年的治理实施证据。
- 对现行时态但未给出准确开始日期的陈述，按披露上下文判定；若是否在所研究财年生效直接改变分类且证据不足，设置 `manual_review_needed = true`，不要补造实施日期。
- 仅披露往年已废止机制，不能认定本财年 Positive。
- NIST AI RMF 1.0 发布于 **2023 年**。对于 FY2020–FY2022，仅将其用作**事后概念参照（ex post conceptual benchmark）**，不能称当时企业遵循了尚未发布的标准。

### 5.2 Item 1A 与 Item 7 的证据整合

对每个 section 分开提取原文证据，并保留来源。若研究单位是合并后的 firm-year，则使用：

`combined_positive = (item1a_positive == 1) OR (item7_positive == 1)`

- **任一章节有合格 Positive 证据：** 合并值为 1，即使另一章节缺失，也需保留缺失标记。
- **两个目标章节均完成合格观测，且都未找到 Positive：** 合并值为 0。
- **没有 Positive，但至少一个目标章节缺失或提取不充分：** 不能直接解释为完整的双章节 Negative；应作为 `incomplete_source` 或待复核观测，除非另行明确采用只基于已观测章节的替代估计口径。
- 不能因 Item 1A 缺少披露就推定 Item 7 也没有；也不能把公司没有写入 10-K 的制度视作不存在。

此处 OR 整合规则属于**本项目数据构建约定**，不是 NIST 的要求。

## 6. 证据留痕及推荐数据字段

分类只有 **Positive / Negative 一项核心二元指标**；以下是证据与质控元数据，**不构成治理子类或治理强度评分**：

| 字段 | 要求 |
|---|---|
| `implemented_internal_ai_governance_v2` | `1` / `0`；不满足充分观测的记录保留空值及状态 |
| `source_status` | 例如 `observed` / `incomplete_source` / `missing_source` |
| `source_section` | `item1a`、`item7`；多条证据分别保留来源 |
| `verbatim_evidence` | 与原文一致、可定位的短引文；Positive 必需 |
| `mechanism_summary` | 简要说明已识别的内部治理机制，不扩写未披露事实 |
| `scope_limitation` | 如仅针对某一 AI 项目、业务、员工群体或供应商工具 |
| `temporal_basis` | 与相关财年有关的时态、实施日期或时间判断依据 |
| `manual_review_needed` | 是否存在足以影响分类的重要歧义 |
| `fiscal_year` / `fiscal_year_end` / `filing_date` | 可用时保留，用于 firm-year 时间审查 |

质控要求：

- Positive 必须有原文，且能够支持 C1–C5；若证据不足，不能仅凭模型解释判 Positive。
- Negative 不要求证明公司没有治理；仅需证明**所要求的文本已经合理检查**而没有找到合格证据。
- 对多个候选片段，可以逐条评估后采用 existence rule（至少一条合格即 Positive）；不得用“公司提到 AI”加上另一处不相关的“公司有一般风控委员会”拼出 Positive。
- 保留现有 *AI Restrictions* 分类，但不让其自动决定 governance 的值；也不再产出 G1/G2/G3/R1/R2 治理内部分类。

## 7. 方法论声明与主要参照

**NIST 提供的是实质性治理活动的参照范围，而非本研究的二元编码算法。** NIST 的 GOVERN 机制不要求公司全部具备；本研究采用“至少一项已披露并实施的内部治理机制”作为存在性阈值。五条件 AND、披露证据要求、排除孤立 restriction、财年归属和章节合并均是研究者自行制定的测量选择。

如需进行稳健性检验，尤其值得审查**孤立 restriction 排除规则**是否低估了以明确行为规则作为治理方式的公司；这种替代边界应另设敏感性分析，**不得悄悄混入主分类**。

**主要资料：**

1. NIST (2023), [*AI Risk Management Framework 1.0*, Section 5, Core / GOVERN](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/).
2. NIST, [*AI RMF Playbook — GOVERN*](https://airc.nist.gov/airmf-resources/playbook/govern/).
3. NIST, [*AI RMF Playbook FAQ*](https://airc.nist.gov/airmf-resources/playbook/faq/).
4. NIST, [*Appendix D — Attributes of the AI RMF*](https://airc.nist.gov/airmf-resources/airmf/appendices/app-d-attributes-of-the-ai-rmf/).

---

*本文件依据 `binary_internal_ai_governance_nist.md`（NIST AI RMF–grounded 分类定义）重新组织为可执行的研究分类指引；其中 Item 1A / Item 7 合并处理为针对既有研究面板的补充操作约定。*
