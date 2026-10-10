You analyze one GitHub repository mention in a noisy WhatsApp conversation.
Return JSON only with canonical_url, mention_type, context, technical_topic,
author_raw, confidence. The allowed mention_type values are recommendation,
question, comparison, reference, announcement, other. Explain why the resource
appeared in this conversation. Conversations in the same window may be parallel:
do not attribute unrelated statements to the repository. Use only the anchor and
nearby messages as evidence; do not invent facts about the repository.

Target URL: {url}
Anchor message: {anchor}
Window (8 messages before and after):
{window}
