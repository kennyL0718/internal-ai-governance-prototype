"""Item 7 context adaptation; substantive governance criteria and schema unchanged."""
from .implemented_governance_prompt import SYSTEM_PROMPT as ORIGINAL

PROMPT_VERSION = 'item7-implemented-governance-v1'
SYSTEM_PROMPT = ORIGINAL.replace(
    'Code a saved US 10-K Item 1A AI-anchor passage',
    'Code the COMPLETE saved US 10-K Item 7 (MD&A) text'
).replace('supplied passage or adjacent context', 'supplied complete Item 7 text') + '''

ITEM 7 APPLICATION INSTRUCTIONS:
Apply the substantive G1/G2/G3/R1/R2 definitions above unchanged to Item 7.
The historical criteria describe Item 1A candidate screening; for this task the
input is the COMPLETE Item 7. Read the entire supplied text. No keyword-based
negative shortcut is allowed. The output risk_factor_heading key is retained
for schema compatibility: use the actual MD&A subsection heading, if available.
AI investment, capital expenditures, R&D, products, efficiency gains, cost savings
and financial results alone do not establish internal AI governance. A present
internal AI control, review, policy or oversight arrangement may qualify under
the same criteria. A cross-reference to Item 1A or another section does not prove
implementation; use only substantive evidence actually present in this Item 7.
No other chapter's labels or evidence are supplied. Do not infer them.
Return every supported overlapping subtype. Quotes must be exact, contiguous
text in the supplied Item 7. Give concise reasoning and keep JSON compact.
'''
