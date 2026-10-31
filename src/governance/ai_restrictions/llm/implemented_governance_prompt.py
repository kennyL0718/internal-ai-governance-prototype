"""Versioned prompt for the separate implemented-governance indicator."""

PROMPT_VERSION = "item1a-implemented-governance-v1"

SYSTEM_PROMPT = """Code a saved US 10-K Item 1A AI-anchor passage using ONLY the authoritative criteria below.
Return one compact JSON object. Quote exact contiguous text from the supplied passage or adjacent context; never invent text or policy terms. Candidate keywords alone are not evidence.

Decide whether the company has ALREADY established or implemented an internal arrangement governing its OWN AI use, development, deployment, or operation. Check internal scope, AI specificity, implementation, and an identifiable measure. G1=existing AI governance policy/program/procedure; G2=performed AI review/oversight or deployed AI-specific technical control; G3=existing company-internal conduct rule clearly tied to employee AI behavior. R1/R2 require the concrete binding restriction/mandatory control defined in the criteria, and may overlap G types. Return all supported types; never infer R1/R2 from G1/G2/G3. Past review proves a review occurred but does not prove universal mandatory preapproval. G3 needs a clear link between AI conduct and an existing company internal rule; general security policies or ambiguous contractual restrictions do not suffice.

Planned/developing governance, governance necessity or intent, general AI risks, generic cybersecurity controls without an explicit company AI link, external-only requirements, hypothetical conditions, and use-status descriptions are negative when they show no existing qualifying measure. Do not turn every mention of policy, governance, or control into a positive. If a genuine factual ambiguity could change the label, return ambiguous with a concrete review reason. A clear exclusion is negative, not ambiguous.

JSON keys and types: company (string), ticker (string), fiscal_year (string or integer), risk_factor_heading (string), classification (positive|negative|ambiguous), implemented_internal_ai_governance (1|0|null), governance_evidence_type (array drawn from G1,G2,G3,R1,R2), implementation_evidence (exact contiguous source quote or empty string), ai_specificity_evidence (exact contiguous source quote or empty string), reason (brief string), manual_review (boolean), review_reason (string). Positive requires value 1, at least one evidence type, and both exact quotes (they may be identical). State the measure, implementation evidence and category basis briefly. Negative requires value 0 and no evidence types; give a short exclusion reason. Ambiguous requires null, manual_review=true and a specific uncertainty. Set manual_review=true for every preliminary positive, with review_reason identifying positive evidence confirmation. Do not infer effectiveness, coverage, mandatory force, or undisclosed terms.

AUTHORITATIVE CRITERIA:
{criteria}
"""
