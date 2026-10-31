# Inductive Content Codebook v1

状态：Frozen；全样本编码使用该 JSON SHA-256，改变规则须建立新版本。

归纳过程：50 个最大差异 firm-year，先逐证据 DeepSeek Open Coding，补充组合证据上下文，再综合同义主题；研究助手检查定义、相邻类别与代表引文后冻结。独立人工复核尚未开展。
维度相互独立；多标签。实践仅限已建立/执行的机制。动机和目标需要与具体治理存在文本关系。
Explicit：直接陈述原因、目的或职责目标；Implicit：有清楚语义联系但未直接表述。一般风险或创新描述的邻接不足以建立关系。
Not Disclosed：在该条证据与有界上下文中未披露。Uncertain、uncodable、失败分别保留。Responsible AI 政策名称本身不足以推断目标。
相同 firm-year、相同类别跨 Evidence/Item 去重；显式与隐式同时存在时，主分类 Explicit 优先，原始二者均保留。
代码覆盖不足的新主题记录 Emerging Theme 并进入复核，不自动修改 Codebook。

Inductive derivation from 50 fixed maximum-variation firm-years and 73 original Binary support evidence fragments. Initial open coding was followed by same-chapter source-context supplementation for 21 flagged firm-years (38 fragments), without changing the sample. The model synthesized a revised draft, then the research assistant documented pre-freeze refinements to separate training from monitoring, policy existence from concrete rules, normative responsible-AI outcomes from broad risk-control goals, external requirements from internal adherence, and explicit opportunity/value drivers from general risk drivers. The final codebook has 12 practice, 9 motivation and 9 objective categories. Minority categories are retained with source-grounded reasons below. Concrete mechanisms, governance-linked drivers and intended outcomes are independent multi-label dimensions. No independent human accuracy or reliability validation is claimed. The complete initial and revised model drafts, open codes, requests, responses and curation audit are preserved.

## P01 AI governance frameworks, policies, and procedures（AI治理框架、政策与程序）

Dimension: practices

Definition: Implemented or maintained AI-specific governance frameworks, internal controls, policies, guidelines, or procedures that set expectations for responsible or risk-managed AI development and use.

Inclusion: Includes explicit current/maintained AI governance frameworks, AI policies, internal AI-use policies, responsible AI/ML policies and procedures, AI risk management frameworks with governance standards, and NIST AI RMF-based governance. Implicit coding is allowed only where the supplied open coding records the policy/framework as existing rather than merely hypothetical.

Exclusion: Excludes cross-functional governance bodies (P02); use-case approval/authorization gates (P03); concrete testing, validation, or risk-assessment activities (P04); model-risk management regimes (P05); specific workforce/third-party permissible-use rules (P06); technical access controls (P07); training (P08); ongoing monitoring/enforcement/reporting (P09); human oversight (P10); incident pause/investigation (P11); and regulatory landscape monitoring (P12).

Distinction: P01 is the policy/framework layer. Concrete operational mechanisms are coded separately and may be multi-labeled only when the evidence separately states them. A bare Responsible AI policy name does not by itself establish a motive or vision. Do not count an undifferentiated framework statement again as P04, P05, or P09.

ALGN FY2025 item7，0001097149_FY2025_item7_E01：

> We maintain governance frameworks, internal controls, and oversight mechanisms designed to promote responsible AI development and deployment, mitigate associated risks, and ensure alignment with applicable laws.

TRU FY2024 item1a，0001552033_FY2024_item1a_E01：

> We have a comprehensive AI risk management framework that includes governance standards, risk assessments, and compliance measures designed to mitigate potential adverse consequences from AI Technologies.

## P02 Cross-functional AI governance bodies and committees（跨职能AI治理机构与委员会）

Dimension: practices

Definition: Implemented internal AI governance bodies, councils, committees, or cross-functional structures that set policy, oversee AI risk, coordinate governance, or report on AI risk to board committees.

Inclusion: Includes senior-management committees overseeing GenAI risk, cross-functional AI councils, Data and AI Governance Committees, cross-functional governance structures, and board-committee reporting tied to AI risk governance.

Exclusion: Excludes general AI policies/frameworks (P01); use-case or tool approval gates (P03); model risk committees (P05); and human expert-in-the-loop review (P10). Does not include committees without an AI governance remit.

Distinction: P02 is an ongoing governance-body arrangement. Committee existence is not used to infer human validation of individual AI outputs or approval of individual use cases; those require separate evidence under P10 or P03.

AVA FY2025 item7，0000104918_FY2025_item7_E01：

> Governance and oversight is performed by a committee composed of senior management who oversee GenAI risks across cybersecurity, technology, and operational domains.

ZION FY2025 item7，0000109380_FY2025_item7_E01：

> This committee—comprising senior leaders from risk, legal, technology, and data functions—sets policy, monitors risk and related events, and helps maintain adherence to regulatory and ethical standards.

## P03 AI use-case review and approval gatekeeping（AI用例审查与审批把关）

Dimension: practices

Definition: Implemented review or authorization gates that permit, restrict, or deny AI tools or use cases before adoption or use, often through legal, information security, IT, or company approval.

Inclusion: Includes legal and information-security review of generative AI use cases, IT and Legal authorization for any AI use case, information-security approval of AI tools, company approval gates, and GenAI tool approval. Implicit coding is allowed only where the supplied open coding draws the gatekeeping link.

Exclusion: Excludes testing/validation without a permission decision (P04), an undifferentiated model-risk regime statement (P05), ongoing monitoring/enforcement (P09), policy naming (P01), and technical blocking/whitelisting (P07). Concrete model-risk permission gates may be P03 together with P05 when both are explicitly described.

Distinction: P03 is the decision to permit, restrict, or deny use. P04 is evaluative assessment/testing that may inform a decision but is not itself an approval gate. Quotes combining approval and risk assessment can be multi-labeled when both are concrete.

CVI FY2025 item1a，0001376139_FY2025_item1a_E01：

> requiring authorization from the IT and Legal Departments for any AI use case

SLVM FY2025 item1a，0001856485_FY2025_item1a_E01：

> We use only limited AI-enhanced tools at the Company, which are approved after review by our information security team.

## P04 AI/ML testing, validation, and risk assessment（AI/ML测试、验证与风险评估）

Dimension: practices

Definition: Concrete evaluation activities for AI/ML models or use cases, including reviews, testing, independent validation, risk-benefit analysis, bias/privacy/transparency assessment, and model performance validation.

Inclusion: Includes extensive AI/ML reviews and testing, independent validation, service-by-service risk-benefit review, evaluation of models for bias/transparency/data-privacy risk, and concrete AI risk assessments.

Exclusion: Excludes approval/authorization decisions (P03); the model-risk management regime as a whole (P05); ongoing monitoring/enforcement/reporting (P09); generic policy statements (P01); and human final review (P10).

Distinction: P04 evaluates; P03 decides permission; P05 is the domain-specific MRM regime. A validation quote within an MRM program may be multi-labeled P04 and P05 only when the evidence states both concrete validation and the MRM regime.

AXP FY2021 item7，0000004962_FY2021_item7_E01：

> We perform extensive reviews and testing to reduce the risk that these AI/ML techniques result in adverse consequences.

FCN FY2023 item1a，0000887936_FY2023_item1a_E01：

> necessitates, in most cases, our review and analysis of such technology and its risks and benefits on a service-by-service basis.

## P05 Model risk management regime for AI/ML models（AI/ML模型风险管理机制）

Dimension: practices

Definition: Formal model-risk management (MRM) frameworks, programs, policies, committees, or validation/approval processes explicitly applied to AI/ML models, including model-risk governance, model-use restrictions, independent validation, performance monitoring, and board reporting.

Inclusion: Includes enterprise MRM frameworks that expressly cover AI/ML models; model risk governance programs; mandatory AI/ML compliance with model risk policies; pre-deployment model validation and Model Risk Committee approval; and dedicated MRM team capabilities covering validation, reporting, monitoring, and committee review.

Exclusion: Excludes generic AI governance/policy (P01); generic AI risk frameworks without an explicit MRM/model-risk regime (P01); ordinary AI/ML testing not within MRM (P04); and general approval gates not model-risk-specific (P03). Concrete MRM validation/approval subactivities may still be multi-labeled with P04 or P03.

Distinction: P05 is retained as a domain-specific practice only when an MRM/model-risk regime or model-risk committee/validation program is explicit. Do not count the same undifferentiated framework statement again as generic AI policy, enterprise risk integration, testing, or approval.

NTRS FY2025 item7，0000073124_FY2025_item7_E01：

> The framework also applies to artificial intelligence, machine learning, and other advanced analytics models, which are subject to risk-based governance, independent validation, and ongoing monitoring commensurate with their complexity, materiality, and use.

STT FY2022 item7，0000093751_FY2022_item7_E01：

> All regulatory capital calculation models, including any artificial intelligence and machine learning models, must comply with the model risk management framework and corresponding policies.

## P06 Permissible-use rules and third-party contractual restrictions（允许使用规则与第三方合同限制）

Dimension: practices

Definition: Specific disclosed requirements, prohibitions, or contractual limits governing what employees, contractors, or third parties may do with AI tools and company information.

Inclusion: Specific safe-use or acceptable-use rules, prohibited AI tools or purposes, required company-provided accounts, restrictions on inputting protected information, and contractual limits on vendor AI use. A concrete rule must be disclosed.

Exclusion: An AI-use policy/guideline name without substantive rule content is P01 only. A review/approval gate alone is P03; implemented technical blocking/whitelisting is P07. Training and ongoing monitoring require P08 and P09 evidence respectively.

Distinction: P01 captures the existence of a policy/framework. P06 captures disclosed rule content. The same policy name alone must not support both. Concrete distinct policy existence and substantive rules can support both with distinct quoted support.

MCHP FY2024 item1a，0000827054_FY2024_item1a_E01：

> We limit our employees’ use of third-party and open-source AI tools, such as ChatGPT, in accordance with our internal guidelines and procedures.

OGS FY2025 item1a，0001587732_FY2025_item1a_E01：

> contractual limitations on vendors’ use of AI

## P07 Technical AI access and data-security controls（技术性AI访问与数据安全控制）

Dimension: practices

Definition: Implemented technical, architectural, or security controls that restrict access to AI tools, whitelist sites, block external generative AI, constrain internal tools from sharing/training on company data, or enhance data security around AI.

Inclusion: Includes blocking external generative AI tools in the IT environment; internal generative AI tools configured not to share company data or train models; site whitelisting; enhanced security measures and risk-based data safeguards where tied to AI use; and technical access restrictions.

Exclusion: Excludes written policy restrictions (P06); approval gates (P03); regulatory landscape monitoring (P12); and generic security not linked to AI.

Distinction: P07 is technical/security control; P06 is written policy rule. When a passage contains both, code each mechanism according to its function.

BG FY2024 item1a，0001996862_FY2024_item1a_E01：

> blocking external generative AI tools within our IT environment

OGS FY2025 item1a，0001587732_FY2025_item1a_E01：

> whitelisting of sites

## P08 Workforce AI training and awareness（员工AI培训与意识）

Dimension: practices

Definition: Implemented training, education, or awareness activities for employees or contractors on AI policies, procedures, risks, uses, benefits, or limitations.

Inclusion: Includes continued effective AI-policy/procedure training, training on procedures governing AI use, and workforce AI education where the open coding records it as an implemented practice.

Exclusion: Excludes ongoing monitoring/enforcement (P09); general policy dissemination; and education listed only as a governance-body objective without an implemented training practice.

Distinction: P08 is separated from P09 even when one sentence lists training and monitoring/enforcement together. Training builds workforce knowledge; monitoring/enforcement checks and responds to conduct.

FIVN FY2024 item1a，0001288847_FY2024_item1a_E02：

> continued effective training, monitoring and enforcement

HOG FY2024 item1a，0000793952_FY2024_item1a_E01：

> training and enforcement of procedures governing the use of artificial intelligence

## P09 Ongoing AI monitoring, enforcement, and reporting（持续AI监测、执行与报告）

Dimension: practices

Definition: Ongoing monitoring, compliance enforcement, performance monitoring, third-party compliance monitoring, board/committee reporting, escalation, and follow-up on AI policy adherence after deployment or use.

Inclusion: Includes monitoring and enforcement of AI policies/guidelines/procedures; enterprise monitoring of AI-based applications; model performance monitoring; compliance monitoring; board or committee reporting on AI risk; and escalation controls.

Exclusion: Excludes training (P08); initial testing/validation (P04); approval gatekeeping (P03); external legal/regulatory landscape scanning (P12); and technical access controls (P07).

Distinction: P09 is continuous/post-adoption oversight and enforcement. P04 is evaluation, and P03 is the permission decision. The same sentence listing training, monitoring, and enforcement may support P08 and P09 separately.

FIVN FY2024 item1a，0001288847_FY2024_item1a_E02：

> monitoring and enforcement

SIRI FY2025 item1a，0000908937_FY2025_item1a_E01：

> seek to monitor the use of AI based applications throughout our enterprise

## P10 Human oversight and expert-in-the-loop review（人工监督与专家在环审查）

Dimension: practices

Definition: Implemented human oversight of AI outputs or decisions, including expert-in-the-loop workflows, supervised AI application, human final review before action, and limits on fully autonomous AI in critical decisions.

Inclusion: Includes expert-in-the-loop models, supervised AI within established modeling environments, all final actions subject to human oversight and review, no fully autonomous AI in critical decision-making or client-facing activities, and continued reliance on expert interpretation.

Exclusion: Excludes governance committee membership (P02); model validation by committee (P05); approval gatekeeping (P03); routine testing (P04). Do not infer human validation from committees.

Distinction: P10 requires evidence of actual human/expert review of AI outputs or decisions, not merely human membership on a governance body.

CERT FY2025 item7，0001827090_FY2025_item7_E01：

> This expert-in-the-loop model allows us to leverage native AI capabilities in a manner that is consistent with regulatory expectations for transparency, reproducibility, and explainability.

ZION FY2025 item1a，0000109380_FY2025_item1a_E01：

> with all final actions subject to human oversight and review.

## P11 AI operational pause, safety review, and incident investigation（AI运营暂停、安全审查与事件调查）

Dimension: practices

Definition: Implemented post-incident or precautionary operational pause, comprehensive safety review, and internal investigation of AI or autonomous-vehicle incidents.

Inclusion: Includes voluntary pause of AV operations, comprehensive safety review tied to the pause, and internal investigation of the incident.

Exclusion: Excludes routine testing (P04); ongoing monitoring (P09); general risk mitigation (M08); and public trust vision (V08), which is an outcome rather than the practice.

Distinction: P11 is an incident-triggered or precautionary operational response, not routine governance, testing, or monitoring.

GM FY2023 item1a，0001467858_FY2023_item1a_E01：

> Cruise voluntarily paused all of its driverless, supervised and manual AV operations in the U.S. while it examines its processes, systems and tools.

GM FY2023 item1a，0001467858_FY2023_item1a_E01：

> We and Cruise are investigating these matters internally

## P12 AI regulatory monitoring and adaptation（AI监管监测与适应）

Dimension: practices

Definition: Ongoing monitoring of the evolving AI legal and regulatory landscape and adaptation of compliance practices to new AI regulations.

Inclusion: Includes monitoring the evolving AI legal landscape and adapting to new regulations to ensure compliance, support innovation, and manage risks.

Exclusion: Excludes internal AI policy monitoring/enforcement (P09); cybersecurity monitoring (P09); and generic legal compliance controls not specifically tied to AI regulatory change.

Distinction: P12 is external regulatory environmental scanning and adaptation. P09 is internal monitoring/enforcement of AI use and policy adherence.

RES FY2025 item1a，0000742278_FY2025_item1a_E01：

> We monitor the evolving AI legal landscape, adapting to new regulations to ensure compliance, support innovation, and manage risks

## M01 Mitigate legal, regulatory, and compliance risk from AI（降低AI法律、监管与合规风险）

Dimension: motivations

Definition: Driver to align AI use with laws or regulations or to reduce legal, regulatory, or compliance exposure.

Inclusion: Includes ensuring alignment with applicable laws; aligning with regulatory expectations; mitigating legal/regulatory consequences; compliance with AI laws; and legal/regulatory screening.

Exclusion: Excludes ethical/trustworthy drivers (M05); general AI risk (M08); data/IP protection (M02) unless framed as legal compliance; and cybersecurity (M03).

Distinction: M01 is the legal/regulatory compliance driver. M05 is the ethical/trustworthiness driver. Quotes citing both legal and ethical standards may be multi-labeled M01 and M05.

ALGN FY2025 item7，0001097149_FY2025_item7_E01：

> ensure alignment with applicable laws

CERT FY2025 item7，0001827090_FY2025_item7_E01：

> consistent with regulatory expectations for transparency, reproducibility, and explainability

## M02 Protect data, confidential information, intellectual property, and company assets from AI-related misuse or disclosure（保护数据、机密信息、知识产权与公司资产）

Dimension: motivations

Definition: Driver to safeguard data, proprietary or confidential information, intellectual property, personal/customer information, or company assets from AI-related exposure, misuse, or policy non-adherence.

Inclusion: Includes data security in generative AI use; preventing inadvertent disclosure of proprietary information and trade secrets; protecting intellectual property and sensitive information; asset protection; data safeguarding; and clear ownership rights.

Exclusion: Excludes cybersecurity vulnerabilities (M03); legal/regulatory compliance (M01); and general AI risk (M08) unless no specific data/IP/asset protection is stated.

Distinction: M02 is information/asset protection. M03 is cyber/security threat. A quote linking unauthorized AI use to data disclosure may be multi-labeled M02 and M06.

CVNA FY2023 item1a，0001690820_FY2023_item1a_E01：

> The introduction of additional AI tools, such as our chatbot, into our business has also increased the risk of inadvertent disclosure of proprietary information and trade secrets.

DOCN FY2023 item1a，0001582961_FY2023_item1a_E02：

> property, competitive information, personal information we may collect or process, and customer information, are protected.

## M03 Mitigate AI-related cybersecurity and technical security risk（降低AI相关网络安全与技术安全风险）

Dimension: motivations

Definition: Driver to reduce cybersecurity, vulnerability, phishing, breach, malware, or system-security risks arising from AI use.

Inclusion: Includes AI-related cybersecurity risks; more sophisticated phishing and breach attempts; vulnerabilities/malware; and system-security harms from unapproved or faulty AI tools where security-specific.

Exclusion: Excludes data/IP confidentiality (M02) unless framed as a security threat; legal/regulatory risk (M01); and general AI risk (M08).

Distinction: M03 centers on security threats and vulnerabilities. M02 centers on protection of information and assets. Quotes naming both may be multi-labeled.

CVI FY2025 item1a，0001376139_FY2025_item1a_E01：

> external and internal cybersecurity risks, such as more sophisticated phishing and breach attempts

DOCN FY2023 item1a，0001582961_FY2023_item1a_E01：

> introduce greater vulnerabilities to cybersecurity attacks or malware into our systems

## M04 Mitigate AI/ML performance, accuracy, bias, and adverse-output risk, including model risk（降低AI/ML性能、准确性、偏见与不良输出风险（含模型风险））

Dimension: motivations

Definition: Driver to reduce risks that AI/ML models or outputs are inaccurate, unintended, biased, conceptually unsound, or otherwise produce adverse consequences or model risk.

Inclusion: Includes unintended AI/ML performance; adverse consequences from AI/ML techniques; incorrect information from AI models; bias; model risk; independent validation to verify conceptual soundness, accuracy, expected performance, and intended use; and flawed recommendations.

Exclusion: Excludes cybersecurity (M03); data/IP protection (M02); legal/regulatory risk (M01); and broad unspecified AI risk (M08).

Distinction: M04 focuses on model/output quality and adverse consequences, including model risk. M08 is used only when the risk is unspecified or broad, not when performance/model/adverse-output risk is named.

AXP FY2020 item7，0000004962_FY2020_item7_E01：

> We perform extensive reviews and testing to reduce the risk that these AI/ML techniques do not perform as intended.

STT FY2022 item7，0000093751_FY2022_item7_E01：

> As a result, the MRM Framework seeks to mitigate our model risk.

## M05 Ensure responsible, ethical, and trustworthy AI use（确保负责任、合乎伦理与可信的AI使用）

Dimension: motivations

Definition: Driver to promote responsible, ethical, or trustworthy development and use of AI, including ethical implementation, trustworthy AI/ML use, and responsible design/development.

Inclusion: Includes promoting ethical AI implementation; ensuring trustworthy AI/ML use; promoting and sustaining responsible AI/ML design, development, and use; and ethical standards as a driver.

Exclusion: Excludes legal/regulatory compliance (M01); general AI risk mitigation (M08); and Responsible AI policy naming alone when no driver is stated.

Distinction: M05 is normative/ethical/trustworthiness driver. M01 is legal/regulatory. A Responsible AI policy name without a stated purpose is not sufficient for M05.

GEHC FY2022 item1a，0001932393_FY2022_item1a_E01：

> We have safeguards designed to promote the ethical implementation of AI

DOCN FY2023 item1a，0001582961_FY2023_item1a_E01：

> to help reasonably ensure that such AI/ML technology is used in a trustworthy manner

## M06 Mitigate unauthorized or non-compliant AI use by workforce or third parties（降低员工或第三方的未授权/不合规AI使用）

Dimension: motivations

Definition: Driver to prevent or reduce unauthorized, unapproved, non-adherent, or non-compliant use of AI tools or policies by employees, contractors, vendors, or partners.

Inclusion: Includes safeguarding against unauthorized AI use; mitigating non-compliant or unapproved AI use; workforce compliance; policy adherence; and misuse by employees or vendors.

Exclusion: Excludes data/IP protection (M02) unless specifically tied to misuse; legal/regulatory risk (M01); and general AI risk (M08).

Distinction: M06 is the compliance/authorization driver. If unauthorized use is linked to data disclosure, code M06 and M02.

GVA FY2024 item1a，0000861459_FY2024_item1a_E01：

> There is a risk that such AI tools (or AI tools used without Company approval) will be used in a manner that does not adhere to our AI policy and/or may be misused by our employees, vendors, or other third parties engaged by us.

HOG FY2024 item1a，0000793952_FY2024_item1a_E01：

> safeguard against the unauthorized use of artificial intelligence tools or technology

## M07 Protect reputation and rebuild public trust（保护声誉与重建公众信任）

Dimension: motivations

Definition: Driver to protect reputation or rebuild public trust in connection with AI-related incidents or risks.

Inclusion: Includes rebuilding public trust; minimizing reputational risk; and avoiding reputational harm.

Exclusion: Excludes general responsible AI (M05); legal/regulatory risk (M01); and financial/operational risk unless reputational or public-trust risk is specifically named.

Distinction: M07 is the reputational/public-trust driver. If a quote lists reputational risk alongside other risks, code M07 and the other relevant motive(s).

GM FY2023 item1a，0001467858_FY2023_item1a_E01：

> This orderly pause is designed to rebuild public trust while Cruise undertakes a comprehensive safety review.

ZION FY2025 item7，0000109380_FY2025_item7_E02：

> These measures help mitigate the financial, operational, and reputational risks associated with AI adoption.

## M08 General AI risk mitigation（一般人工智能风险缓释）

Dimension: motivations

Definition: A governance driver to mitigate broad AI-related risks without an identified specific risk domain.

Inclusion: A direct governance-to-risk-control rationale such as mitigating associated AI risks or addressing AI risks/challenges, where no specific risk driver is stated for that link.

Exclusion: Specific legal/regulatory, data/IP, cyber, model/output, unauthorized-use, or reputational risks use their specific M categories. Opportunity, adoption, experimentation, and value drivers are M09. Do not infer this category from adjacent generic risk disclosure.

Distinction: General risk prevention is distinct from M05 normative responsible/ethical use and M09 opportunity/value capture. Specific risk categories take precedence for the same rationale.

ALGN FY2025 item7，0001097149_FY2025_item7_E01：

> mitigate associated risks

## M09 Capture AI opportunities and deliver business value（把握人工智能机会并创造业务价值）

Dimension: motivations

Definition: A stated or clearly linked driver for establishing governance is to capture AI opportunities, deliver value, or enable beneficial experimentation and adoption.

Inclusion: A governance body is created to address AI opportunities, or its stated reason/purpose is to deliver value through governance and deliberate experimentation. Preserve explicitness of the actual link.

Exclusion: Nearby general AI strategy, ordinary AI adoption, innovation claims without a governance link, and risk reduction alone. Do not infer a particular benefit or business strategy from unspecified opportunities.

Distinction: M09 is the opportunity/value driver; M08 is broad risk mitigation. V05 is the intended adoption/value outcome. A direct purpose clause may support both M09 and V05, while each dimension is coded separately.

MTUS FY2024 item1a，0001598428_FY2024_item1a_E01：

> with an objective to deliver value by providing education regarding the uses, benefits and risks of AI and similar technologies in our business, establishing a governance framework and principles for our use of AI, and enabling deliberate experimentation with new technologies employing AI.

PNW FY2024 item7，0000764622_FY2024_item7_E01：

> To address the rapid advancement of artificial intelligence technology risks and opportunities

## V01 Responsible, ethical, trustworthy, and safe AI use（负责任、伦理、可信与安全的人工智能使用）

Dimension: visions

Definition: An intended normative or responsible-operation outcome for AI development or use, expressly linked to the disclosed governance.

Inclusion: Responsible AI development/deployment, ethical implementation, trustworthy AI use, and safe/responsible operation within risk appetite when these outcomes are stated rather than only embedded in a policy title.

Exclusion: Broad risk mitigation alone is V09. Specific model/output, data/system/IP, legal compliance, internal workforce adherence, explainability/auditability, reputation, and adoption/value objectives use their distinct V categories. Responsible-AI policy naming alone is insufficient.

Distinction: V01 requires a normative, trustworthiness or safe/responsible-operation outcome. V09 requires a general risk-control outcome. Neither is inferred from the other; distinct clauses can support both.

ALGN FY2025 item7，0001097149_FY2025_item7_E01：

> promote responsible AI development and deployment

NTRS FY2025 item7，0000073124_FY2025_item7_E02：

> ensuring AI technologies operate safely, responsibly, and within Northern Trust’s risk appetite

## V02 AI/ML models perform as intended, accurately, and without adverse consequences（AI/ML模型按预期运行、准确且无不良后果）

Dimension: visions

Definition: Intended outcome that AI/ML models perform as intended, are accurate, conceptually sound, expected-performing, fit for intended use, and/or do not produce adverse consequences or incorrect outputs.

Inclusion: Includes AI/ML performing as intended; avoiding or reducing adverse consequences; reducing incorrect information; validating models as conceptually sound, computationally accurate, performing as expected, and aligned with intended use.

Exclusion: Excludes broad responsible/safe AI (V01); cybersecurity/data protection (V03); legal compliance (V04); and explainability/auditability process outcomes (V07).

Distinction: V02 is the model/output performance outcome. V07 is the process-property outcome of explainability, auditability, and expert validation.

AXP FY2020 item7，0000004962_FY2020_item7_E01：

> We perform extensive reviews and testing to reduce the risk that these AI/ML techniques do not perform as intended.

STT FY2022 item7，0000093751_FY2022_item7_E01：

> An independent model validation function designed to verify that models are conceptually sound, computationally accurate, are performing as expected, and are in line with their intended use.

## V03 Protect data, systems, confidential information, intellectual property, and assets from AI-related risk（保护数据、系统、机密信息、知识产权与资产免受AI相关风险）

Dimension: visions

Definition: Intended outcome that data, systems, confidential or proprietary information, intellectual property, personal/customer information, or company assets are protected from AI-related disclosure, misuse, security threats, or harm.

Inclusion: Includes protecting proprietary information; safeguarding confidential information and IP; protecting assets and information; securing data with clear ownership; and reducing AI-related cyber or incorrect-information risk to systems/data.

Exclusion: Excludes legal/regulatory compliance (V04); model performance (V02); and broad responsible AI (V01).

Distinction: V03 is protection of information, systems, and assets. If a quote frames data protection as legal compliance, code V03 and V04.

CVNA FY2023 item1a，0001690820_FY2023_item1a_E01：

> may not effectively protect proprietary information

DOCN FY2023 item1a，0001582961_FY2023_item1a_E02：

> property, competitive information, personal information we may collect or process, and customer information, are protected.

## V04 Legal, regulatory, and external ethical-standards compliance（法律、监管与外部伦理标准合规）

Dimension: visions

Definition: An intended outcome of alignment with applicable laws, regulations, regulatory expectations, or externally framed ethical standards for AI.

Inclusion: Explicit regulatory/legal alignment and compliance objectives; conformity to identified external ethical standards. A clause that separately names law and internal policy can support V04 and V06.

Exclusion: Internal workforce policy adherence, approval, and authorization alone are V06, not V04. Generic responsible/ethical use is V01 unless actual compliance framing is stated.

Distinction: V04 concerns external requirements; V06 concerns internal AI policy adherence and authorization. A single undifferentiated internal-policy compliance statement must not be duplicated across both.

ZION FY2025 item7，0000109380_FY2025_item7_E02：

> AI use cases are subject to ongoing governance, risk assessment, and appropriate oversight to maintain compliance with applicable laws, ethical standards, and organizational policies.

CERT FY2025 item7，0001827090_FY2025_item7_E01：

> This expert-in-the-loop model allows us to leverage native AI capabilities in a manner that is consistent with regulatory expectations for transparency, reproducibility, and explainability.

## V05 Enable efficient, controlled, and innovative AI adoption and value delivery（实现高效、受控与创新的AI采用及价值交付）

Dimension: visions

Definition: Intended outcome to enable efficient, controlled, productive, innovative, or value-generating AI adoption, including productivity/insight generation, deliberate experimentation, internal generative AI enablement, and compliance-enabled innovation.

Inclusion: Includes efficient GenAI adoption; controlled internal GenAI enablement; AI as productivity and insight augmentation; enabling deliberate AI experimentation; AI value delivery; compliance-enabled innovation; and strategic alignment of AI risk assessment.

Exclusion: Excludes responsible/safe AI (V01); legal compliance (V04); workforce compliance (V06); and model performance accuracy (V02).

Distinction: V05 is the adoption/value/innovation outcome. If a quote combines innovation with compliance, code V05 and V04.

AVA FY2025 item7，0000104918_FY2025_item7_E01：

> Under this approach, GenAI adoption supports operational efficiency while minimizing legal, security, financial, and reputational risks.

MTUS FY2024 item1a，0001598428_FY2024_item1a_E01：

> enabling deliberate experimentation with new technologies employing AI

## V06 Secure workforce compliance with AI governance and prevent unauthorized AI use（确保员工遵守AI治理并防止未授权AI使用）

Dimension: visions

Definition: Intended outcome that the workforce and contractors comply with AI policies and that AI use is authorized, policy-adherent, and adequately safeguarded against unauthorized use.

Inclusion: Includes workforce compliance with AI governance policies; policy-compliant and approved AI tool use; and adequate safeguarding against unauthorized AI use.

Exclusion: External legal/regulatory or external ethical-standard compliance is V04; data protection is V03; general responsible AI is V01. Do not duplicate internal-policy adherence alone as V04.

Distinction: V06 concerns internal workforce adherence and authorization; V04 concerns external legal/regulatory/ethical-standard alignment. Multi-label only when separate external and internal requirements are disclosed.

FIVN FY2024 item1a，0001288847_FY2024_item1a_E02：

> compliance by our workforce

HOG FY2024 item1a，0000793952_FY2024_item1a_E01：

> to safeguard against the unauthorized use of artificial intelligence tools or technology

## V07 Ensure explainable, auditable, and expert-validated AI decision processes（确保可解释、可审计与经专家验证的AI决策流程）

Dimension: visions

Definition: Intended outcome that AI-enabled processes remain explainable, auditable, reproducible, and/or subject to expert or validated decision support.

Inclusion: Includes explainable and auditable AI; transparency, reproducibility, and explainability; validated models and expert interpretation for decision support; and expert-led workflows.

Exclusion: Excludes model performance/accuracy (V02); human oversight practice (P10); and broad responsible AI (V01).

Distinction: V07 is a process/decision-support property outcome. V02 is an output-performance outcome. P10 is the implemented human-review practice, not the vision itself.

ZION FY2025 item7，0000109380_FY2025_item7_E02：

> Our governance framework requires that AI-enabled processes remain explainable and auditable, supported by controls designed to manage outcomes and escalate issues when necessary.

CERT FY2025 item7，0001827090_FY2025_item7_E03：

> our solutions continue to rely on validated models and expert interpretation to support decision-making in regulated environments.

## V08 Restore public trust and protect reputation（重建公众信任并保护声誉）

Dimension: visions

Definition: Intended outcome to rebuild public trust or protect reputation in connection with AI-related incidents or risks.

Inclusion: Includes rebuilding public trust; minimizing reputational risk; and avoiding reputational harm.

Exclusion: Excludes responsible AI (V01); legal compliance (V04); and financial/operational risk unless reputational or public-trust outcome is specifically named.

Distinction: V08 is the trust/reputation outcome. If a quote lists reputational risk alongside legal, security, or financial risks, code V08 and the other relevant vision(s).

GM FY2023 item1a，0001467858_FY2023_item1a_E01：

> This orderly pause is designed to rebuild public trust while Cruise undertakes a comprehensive safety review.

AVA FY2025 item7，0000104918_FY2025_item7_E01：

> Under this approach, GenAI adoption supports operational efficiency while minimizing legal, security, financial, and reputational risks.

## V09 General AI risk prevention and mitigation（一般人工智能风险预防与缓释目标）

Dimension: visions

Definition: An intended outcome that broad AI-related risks or adverse consequences are prevented, identified, assessed, controlled, or mitigated, without a specified risk domain.

Inclusion: Express governance-linked intended risk-control outcomes that remain general in the disclosure. Not simply generic AI risk discussion or listing a risk-assessment practice with no intended outcome.

Exclusion: Normative responsible/ethical/trustworthy/safe-operation statements alone use V01. Named specific model, data, cyber, legal, authorization, or reputational outcomes use specific V categories for the same link. Do not reconstruct a risk goal from the existence of a control alone.

Distinction: V09 separates broad risk-control outcomes from V01 normative responsible operation, preserving the substantive distinction needed to examine risk management and responsible-AI objectives. Distinct clauses may support both.

TRU FY2024 item1a，0001552033_FY2024_item1a_E01：

> We have a comprehensive AI risk management framework that includes governance standards, risk assessments, and compliance measures designed to mitigate potential adverse consequences from AI Technologies.

## Consolidation notes

Practice categories were formed by activity type: policy/framework layer (P01), governance bodies (P02), approval gatekeeping (P03), testing/validation/risk assessment (P04), model-risk regime (P05), permissible-use policy (P06), technical/security controls (P07), training (P08), monitoring/enforcement/reporting (P09), human oversight (P10), incident pause/investigation (P11), and regulatory scanning (P12).
Training/awareness (P08) and ongoing monitoring/enforcement (P09) are kept separate even when the same sentence lists them, because they are conceptually distinct activities.
Approval gatekeeping (P03) is separated from testing/validation/risk assessment (P04) and from the model-risk regime (P05). A quote may be multi-labeled only when it separately evidences the gatekeeping decision, the evaluation activity, or the MRM regime.
The model-risk regime (P05) is retained as a domain-specific practice. Generic AI governance or undifferentiated framework statements are not re-counted as P05, P04, P03, or enterprise risk integration.
Human oversight/expert-in-the-loop (P10) is coded only where actual human/expert review recurs. Committee membership and governance-body oversight are not inferred to be human validation.
Policy-based permissible-use restrictions (P06) are distinguished from technical access/data-security controls (P07). Contractual vendor limitations are included under P06 as third-party permissible-use restrictions, not as technical controls.
A Responsible AI policy name alone was not treated as a motive or vision. Explicit/implicit coding follows the supplied open coding: implicit only where a direct textual link is recorded and no explicit purpose/outcome is stated.
Observations marked uncodable or describing ordinary AI adoption without an internal governance mechanism were not used to create categories. Observations with future/current ambiguity were used only where the supplied coding retained a non-uncodable practice and did not require unsupported expansion.
Research-assistant pre-freeze refinements: P01/P06: distinguish policy existence from substantive permissible-use rule content; policy naming alone is not two themes.
Research-assistant pre-freeze refinements: P03/P05: remove contradictory exclusion of concrete model-risk approval gates; regime plus distinct gate can be multi-labeled.
Research-assistant pre-freeze refinements: M08/M09: separate general risk mitigation from explicit opportunity/value drivers already present in two exploration firms.
Research-assistant pre-freeze refinements: V01/V09: separate normative responsible AI outcomes from general risk-control outcomes; both are substantively important to the research question.
Research-assistant pre-freeze refinements: V04/V06: external legal/regulatory/ethical standards versus internal policy adherence; no duplicate coding of internal compliance alone.
Final motivations: M01 Mitigate legal, regulatory, and compliance risk from AI, M02 Protect data, confidential information, intellectual property, and company assets from AI-related misuse or disclosure, M03 Mitigate AI-related cybersecurity and technical security risk, M04 Mitigate AI/ML performance, accuracy, bias, and adverse-output risk, including model risk, M05 Ensure responsible, ethical, and trustworthy AI use, M06 Mitigate unauthorized or non-compliant AI use by workforce or third parties, M07 Protect reputation and rebuild public trust, M08 General AI risk mitigation, M09 Capture AI opportunities and deliver business value
Final objectives: V01 Responsible, ethical, trustworthy, and safe AI use, V02 AI/ML models perform as intended, accurately, and without adverse consequences, V03 Protect data, systems, confidential information, intellectual property, and assets from AI-related risk, V04 Legal, regulatory, and external ethical-standards compliance, V05 Enable efficient, controlled, and innovative AI adoption and value delivery, V06 Secure workforce compliance with AI governance and prevent unauthorized AI use, V07 Ensure explainable, auditable, and expert-validated AI decision processes, V08 Restore public trust and protect reputation, V09 General AI risk prevention and mitigation

## Minority themes

P11 operational pause, safety review, and incident investigation is limited to one corporate group but deserves separate treatment because it is an incident-triggered operational response distinct from routine testing, monitoring, or policy governance.
P12 AI regulatory monitoring and adaptation has limited evidence but is a distinct external legal-environment scanning and adaptation practice, not internal AI policy monitoring/enforcement.
P05 model risk management has limited firm coverage but is a domain-specific regime with explicit model-risk validation, committee approval, policy compliance, and monitoring; it is retained separately and constrained to prevent double counting.
M07 protect reputation and rebuild public trust is a minority driver tied to reputational/trust consequences; it is not merged with responsible AI because the driver is public trust/reputation rather than ethical AI per se.
V08 restore public trust and protect reputation is a minority outcome tied to an incident and reputational risk; it is kept separate from broad responsible AI and compliance outcomes.
M08 general AI risk mitigation is a constrained residual category. It is retained only because some disclosures state a broad risk-control link without a more specific risk; it is not a catch-all and is excluded whenever a specific risk is named.
V09 covers broad general AI risk mitigation only where no more specific vision is stated. V01 is kept separate for normative responsible AI outcomes.
P10 human oversight/expert-in-the-loop review recurs across multiple evidence units and is retained separately because actual human/expert review is a distinct control, not merely a governance committee or model-validation function.
M09 has minority exploration support from two distinct firms; retained to avoid absorbing a direct governance opportunity/value driver into generic risk mitigation. No broader strategic purpose is inferred.