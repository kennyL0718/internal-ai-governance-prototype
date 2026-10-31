"""Documented research-assistant curation of the inductive draft before freeze."""
import sys
import copy
import json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from ai_restrictions import governance_content as g

audit=g.OUT/'codebook_refinement_audit.json'
backup=g.OUT/'codebook_draft_before_refinement.json'
if backup.exists():
    cb=g.read(backup)
    before=g.sha(backup)
else:
    cb=g.read(g.OUT/'codebook_draft.json')
    before=g.sha(g.OUT/'codebook_draft.json')
    g.dump(backup,copy.deepcopy(cb))
cats={c['id']:c for c in cb['categories']}
assert 'general AI risk mitigation' in cats['V01']['name']
assert 'opportunity' in cats['M08']['name']
cats['P03']['exclusion']='Excludes testing/validation without a permission decision (P04), an undifferentiated model-risk regime statement (P05), ongoing monitoring/enforcement (P09), policy naming (P01), and technical blocking/whitelisting (P07). Concrete model-risk permission gates may be P03 together with P05 when both are explicitly described.'
cats['P06'].update(name='Permissible-use rules and third-party contractual restrictions',
    name_zh='允许使用规则与第三方合同限制',
    definition='Specific disclosed requirements, prohibitions, or contractual limits governing what employees, contractors, or third parties may do with AI tools and company information.',
    inclusion='Specific safe-use or acceptable-use rules, prohibited AI tools or purposes, required company-provided accounts, restrictions on inputting protected information, and contractual limits on vendor AI use. A concrete rule must be disclosed.',
    exclusion='An AI-use policy/guideline name without substantive rule content is P01 only. A review/approval gate alone is P03; implemented technical blocking/whitelisting is P07. Training and ongoing monitoring require P08 and P09 evidence respectively.',
    distinction='P01 captures the existence of a policy/framework. P06 captures disclosed rule content. The same policy name alone must not support both. Concrete distinct policy existence and substantive rules can support both with distinct quoted support.')
cats['P06']['examples']=[e for e in cats['P06']['examples'] if e['quote']!='policies relating to the safe use of AI tools']
cats['M08'].update(name='General AI risk mitigation',name_zh='一般人工智能风险缓释',
    definition='A governance driver to mitigate broad AI-related risks without an identified specific risk domain.',
    inclusion='A direct governance-to-risk-control rationale such as mitigating associated AI risks or addressing AI risks/challenges, where no specific risk driver is stated for that link.',
    exclusion='Specific legal/regulatory, data/IP, cyber, model/output, unauthorized-use, or reputational risks use their specific M categories. Opportunity, adoption, experimentation, and value drivers are M09. Do not infer this category from adjacent generic risk disclosure.',
    distinction='General risk prevention is distinct from M05 normative responsible/ethical use and M09 opportunity/value capture. Specific risk categories take precedence for the same rationale.',
    examples=[e for e in cats['M08']['examples'] if 'opportunities' not in e['quote']])
cats['V01'].update(name='Responsible, ethical, trustworthy, and safe AI use',name_zh='负责任、伦理、可信与安全的人工智能使用',
    definition='An intended normative or responsible-operation outcome for AI development or use, expressly linked to the disclosed governance.',
    inclusion='Responsible AI development/deployment, ethical implementation, trustworthy AI use, and safe/responsible operation within risk appetite when these outcomes are stated rather than only embedded in a policy title.',
    exclusion='Broad risk mitigation alone is V09. Specific model/output, data/system/IP, legal compliance, internal workforce adherence, explainability/auditability, reputation, and adoption/value objectives use their distinct V categories. Responsible-AI policy naming alone is insufficient.',
    distinction='V01 requires a normative, trustworthiness or safe/responsible-operation outcome. V09 requires a general risk-control outcome. Neither is inferred from the other; distinct clauses can support both.')
cats['V04'].update(name='Legal, regulatory, and external ethical-standards compliance',name_zh='法律、监管与外部伦理标准合规',
    definition='An intended outcome of alignment with applicable laws, regulations, regulatory expectations, or externally framed ethical standards for AI.',
    inclusion='Explicit regulatory/legal alignment and compliance objectives; conformity to identified external ethical standards. A clause that separately names law and internal policy can support V04 and V06.',
    exclusion='Internal workforce policy adherence, approval, and authorization alone are V06, not V04. Generic responsible/ethical use is V01 unless actual compliance framing is stated.',
    distinction='V04 concerns external requirements; V06 concerns internal AI policy adherence and authorization. A single undifferentiated internal-policy compliance statement must not be duplicated across both.')
cats['V06']['exclusion']='External legal/regulatory or external ethical-standard compliance is V04; data protection is V03; general responsible AI is V01. Do not duplicate internal-policy adherence alone as V04.'
cats['V06']['distinction']='V06 concerns internal workforce adherence and authorization; V04 concerns external legal/regulatory/ethical-standard alignment. Multi-label only when separate external and internal requirements are disclosed.'
new_m=dict(id='M09',dimension='motivations',name='Capture AI opportunities and deliver business value',name_zh='把握人工智能机会并创造业务价值',
    definition='A stated or clearly linked driver for establishing governance is to capture AI opportunities, deliver value, or enable beneficial experimentation and adoption.',
    inclusion='A governance body is created to address AI opportunities, or its stated reason/purpose is to deliver value through governance and deliberate experimentation. Preserve explicitness of the actual link.',
    exclusion='Nearby general AI strategy, ordinary AI adoption, innovation claims without a governance link, and risk reduction alone. Do not infer a particular benefit or business strategy from unspecified opportunities.',
    distinction='M09 is the opportunity/value driver; M08 is broad risk mitigation. V05 is the intended adoption/value outcome. A direct purpose clause may support both M09 and V05, while each dimension is coded separately.',
    examples=[dict(evidence_id='0001598428_FY2024_item1a_E01',quote='with an objective to deliver value by providing education regarding the uses, benefits and risks of AI and similar technologies in our business, establishing a governance framework and principles for our use of AI, and enabling deliberate experimentation with new technologies employing AI.'),
        dict(evidence_id='0000764622_FY2024_item7_E01',quote='To address the rapid advancement of artificial intelligence technology risks and opportunities')])
new_v=dict(id='V09',dimension='visions',name='General AI risk prevention and mitigation',name_zh='一般人工智能风险预防与缓释目标',
    definition='An intended outcome that broad AI-related risks or adverse consequences are prevented, identified, assessed, controlled, or mitigated, without a specified risk domain.',
    inclusion='Express governance-linked intended risk-control outcomes that remain general in the disclosure. Not simply generic AI risk discussion or listing a risk-assessment practice with no intended outcome.',
    exclusion='Normative responsible/ethical/trustworthy/safe-operation statements alone use V01. Named specific model, data, cyber, legal, authorization, or reputational outcomes use specific V categories for the same link. Do not reconstruct a risk goal from the existence of a control alone.',
    distinction='V09 separates broad risk-control outcomes from V01 normative responsible operation, preserving the substantive distinction needed to examine risk management and responsible-AI objectives. Distinct clauses may support both.',
    examples=[dict(evidence_id='0001552033_FY2024_item1a_E01',quote='We have a comprehensive AI risk management framework that includes governance standards, risk assessments, and compliance measures designed to mitigate potential adverse consequences from AI Technologies.')])
cb['categories']=[c for c in cb['categories'] if c['dimension']=='practices']+[c for c in cb['categories'] if c['dimension']=='motivations']+[new_m]+[c for c in cb['categories'] if c['dimension']=='visions']+[new_v]
changes=[
    'P01/P06: distinguish policy existence from substantive permissible-use rule content; policy naming alone is not two themes.',
    'P03/P05: remove contradictory exclusion of concrete model-risk approval gates; regime plus distinct gate can be multi-labeled.',
    'M08/M09: separate general risk mitigation from explicit opportunity/value drivers already present in two exploration firms.',
    'V01/V09: separate normative responsible AI outcomes from general risk-control outcomes; both are substantively important to the research question.',
    'V04/V06: external legal/regulatory/ethical standards versus internal policy adherence; no duplicate coding of internal compliance alone.'
]
cb['consolidation_notes'] += ['Research-assistant pre-freeze refinements: '+s for s in changes]
cb['consolidation_notes']=[s for s in cb['consolidation_notes'] if not s.startswith('Motives were consolidated') and not s.startswith('Visions were consolidated')]
cb['consolidation_notes'] += ['Final motivations: '+', '.join(c['id']+' '+c['name'] for c in cb['categories'] if c['dimension']=='motivations'),
    'Final objectives: '+', '.join(c['id']+' '+c['name'] for c in cb['categories'] if c['dimension']=='visions')]
cb['minority_theme_notes'] += ['M09 has minority exploration support from two distinct firms; retained to avoid absorbing a direct governance opportunity/value driver into generic risk mitigation. No broader strategic purpose is inferred.']
cb['minority_theme_notes']=[s.replace('V01 includes broad general AI risk mitigation only where no more specific vision is stated; this avoids duplicating V02, V03, V04, V06, V07, or V08.','V09 covers broad general AI risk mitigation only where no more specific vision is stated. V01 is kept separate for normative responsible AI outcomes.')
    .replace('M08 general AI risk mitigation and opportunity management','M08 general AI risk mitigation') for s in cb['minority_theme_notes']]
cb['minority_theme_notes']=[s.replace('broad risk-control or opportunity-management link','broad risk-control link') for s in cb['minority_theme_notes']]
cb['derivation']='Inductive derivation from 50 fixed maximum-variation firm-years and 73 original Binary support evidence fragments. Initial open coding was followed by same-chapter source-context supplementation for 21 flagged firm-years (38 fragments), without changing the sample. The model synthesized a revised draft, then the research assistant documented pre-freeze refinements to separate training from monitoring, policy existence from concrete rules, normative responsible-AI outcomes from broad risk-control goals, external requirements from internal adherence, and explicit opportunity/value drivers from general risk drivers. The final codebook has 12 practice, 9 motivation and 9 objective categories. Minority categories are retained with source-grounded reasons below. Concrete mechanisms, governance-linked drivers and intended outcomes are independent multi-label dimensions. No independent human accuracy or reliability validation is claimed. The complete initial and revised model drafts, open codes, requests, responses and curation audit are preserved.'
units={u['evidence_id']:u for u in g.read(g.STATE/'evidence_units.json')}
assert len({c['id'] for c in cb['categories']})==len(cb['categories'])
for c in cb['categories']:
    for e in c['examples']: g.exact_quote(e['quote'],units[e['evidence_id']])
g.dump(g.OUT/'codebook_draft.json',cb)
g.codebook_markdown(cb,False)
g.dump(audit,dict(before_sha256=before,after_sha256=g.sha(g.OUT/'codebook_draft.json'),
    changes=changes,performed_by='research assistant; no independent human reliability study',
    scope='inductive exploration evidence only; before full-sample coding',time_utc=g.now()))
g.log(dict(categories=len(cb['categories']),changes=changes))
