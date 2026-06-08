# Segregation of Duties (IT Operations)

**Citation:** FFIEC IT Examination Handbook — Management  
**Authority:** FFIEC  

## Summary

No single individual should hold both the ability to initiate and to approve transactions affecting financial records.

## Key Requirements

- Separate request, approval, and implementation roles for sensitive changes.
- Prohibit self-approval of wire releases and journal entries.
- Enforce dual control over high-risk operations.
- Review SoD conflicts at least annually.

## Detection Indicators

- Same actor both created and approved a wire or journal entry.
- Developer with standing production-deploy rights.
- Access provisioning performed by the same person who requested it.

## Enforcement

Control-deficiency findings; potential SOX 404 material weakness if it affects financial reporting.

## Source

<https://ithandbook.ffiec.gov/it-booklets/management/>
