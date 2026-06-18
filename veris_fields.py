"""Mapping from the predicted A4 field names to their VERIS enum vocabularies.

Shared by extract_qwen.py (prompt + format schema) and score_rq1.py (validation
+ scoring) so the two never drift. For multi-label fields the allowed vocabulary
is the UNION of the relevant category sub-vocabularies (the spec validates each
array element against that union, since the correct sub-vocab depends on the
chosen category which we do not hard-constrain).
"""
from veris_enums import ENUMS

# Single-label dimensions: field -> enum key (validated against that exact list)
SINGLE_FIELDS = {
    "actor_category":         "actor.category",
    "action_category":        "action.category",
    "asset_category":         "asset.category",
    "attr_conf_present":      "yes_no_unknown",
    "attr_integrity_present": "yes_no_unknown",
    "attr_avail_present":     "yes_no_unknown",
    "attr_conf_disclosure":   "attribute.confidentiality.data_disclosure",
}

# Multi-label dimensions: field -> list of enum keys whose UNION is the vocab
MULTI_FIELDS = {
    "actor_variety": [
        "actor.external.variety", "actor.internal.variety", "actor.partner.variety",
    ],
    "actor_motive": ["actor.motive"],
    "action_variety": [
        "action.malware.variety", "action.hacking.variety", "action.social.variety",
        "action.misuse.variety", "action.physical.variety", "action.error.variety",
        "action.environmental.variety",
    ],
    "action_vector": [
        "action.malware.vector", "action.hacking.vector", "action.social.vector",
        "action.misuse.vector", "action.physical.vector", "action.error.vector",
    ],
    "asset_variety": [
        "asset.server.variety", "asset.user_device.variety", "asset.media.variety",
        "asset.network.variety", "asset.person.variety", "asset.kiosk_terminal.variety",
        "asset.embedded.variety",
    ],
    "attr_conf_data_variety": ["attribute.confidentiality.data.variety"],
    "attr_integrity_variety": ["attribute.integrity.variety"],
    "attr_avail_variety":     ["attribute.availability.variety"],
}

# The eight A4 dimensions averaged for the headline number, in report order.
ALL_FIELDS = list(SINGLE_FIELDS) + list(MULTI_FIELDS)


def allowed_values(field):
    """Return the set of canonical strings allowed for a predicted field."""
    if field in SINGLE_FIELDS:
        return set(ENUMS[SINGLE_FIELDS[field]])
    vals = set()
    for k in MULTI_FIELDS[field]:
        vals.update(ENUMS[k])
    return vals
