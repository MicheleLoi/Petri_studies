"""Reject ambiguous JSON; retained policy from the original registered study."""


def duplicate_guard(pairs):
    result={}
    for key,value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key')
        result[key]=value
    return result
